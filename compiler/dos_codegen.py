from pathlib import Path
import struct

from compiler import ast_nodes as A


class DOSCodegenError(Exception):
    """Raised when a Javelin program cannot be compiled to DOS."""


class DOSCodeGenerator:
    HEADER_SIZE = 32
    MAX_INTEGER = 32767
    MIN_INTEGER = -32768

    def __init__(self):
        self.code = bytearray()
        self.data = bytearray()
        self.labels = {}
        self.fixups = []
        self.next_label = 0
        self.variables = {}
        self.constants = set()
        self.string_labels = {}
        self.terminated = False
        self.needs_number_printer = False
        self.next_data_address = 0x8000

    def compile(self, program, output_path):
        self.code = bytearray()
        self.data = bytearray()
        self.labels = {}
        self.fixups = []
        self.next_label = 0
        self.variables = {}
        self.constants = set()
        self.string_labels = {}
        self.terminated = False
        self.needs_number_printer = False
        self.next_data_address = 0x8000
        # DS = CS, so the program can address its own load image.
        self._emit(0x0E, 0x1F)  # PUSH CS; POP DS

        statements = getattr(program, "statements", None)
        if statements is None:
            raise DOSCodegenError(
                "Program AST does not contain a statements list."
            )

        # The current backend deliberately rejects constructs whose
        # runtime semantics have not yet been implemented.
        for statement in statements:
            self._statement(statement)

        self._emit_exit(0)

        # Place the number-printing subroutine after the main program exit.
        if self.needs_number_printer:
            self._emit_number_printer()

        image = bytearray(self._link())

        # Variables live at fixed offsets in the load segment.
        # Reject oversized code rather than allowing it to overlap data.
        if len(image) > 0x8000:
            raise DOSCodegenError(
                "Generated code exceeds the available code area."
            )

        # Pad the load image until the reserved data region begins.
        image.extend(b"\x90" * (0x8000 - len(image)))

        # Reserve two bytes per allocated variable/counter.
        data_size = self.next_data_address - 0x8000
        image.extend(b"\x00" * data_size)

        exe = self._make_mz_exe(bytes(image))

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(exe)
        return output_path

    # ---------------------------------------------------------
    # Machine-code emission
    # ---------------------------------------------------------

    def _emit(self, *values):
        self.code.extend(value & 0xFF for value in values)

    def _word(self, value):
        self.code.extend(struct.pack("<H", value & 0xFFFF))

    def _new_label(self, prefix="L"):
        label = f"{prefix}{self.next_label}"
        self.next_label += 1
        return label

    def _mark(self, label):
        if label in self.labels:
            raise DOSCodegenError(f"Duplicate internal label: {label}")
        self.labels[label] = len(self.code)

    def _rel16(self, opcode, label):
        self._emit(*opcode)
        operand_position = len(self.code)
        self._word(0)
        self.fixups.append((operand_position, label))

    def _link(self):
        code = bytearray(self.code)

        for position, label in self.fixups:
            if label not in self.labels:
                raise DOSCodegenError(
                    f"Unresolved machine-code label: {label}"
                )

            # Relative displacement is measured from the instruction
            # immediately after the 16-bit displacement.
            displacement = self.labels[label] - (position + 2)

            if not -32768 <= displacement <= 32767:
                raise DOSCodegenError(
                    "Generated branch exceeds the 16-bit range."
                )

            struct.pack_into("<h", code, position, displacement)

        return bytes(code)

    def _emit_exit(self, return_code=0):
        self._emit(0xB8, return_code, 0x4C, 0xCD, 0x21)

    # ---------------------------------------------------------
    # Statements
    # ---------------------------------------------------------

    def _statement(self, node):
        if isinstance(node, A.Declaration):
            if node.name in self.variables:
                raise DOSCodegenError(
                    f"Duplicate variable declaration: {node.name}"
                )

            if node.type_name is not None:
                raise DOSCodegenError(
                    "Explicit type annotations are not supported "
                    "by the current DOS backend."
                )

            self._allocate_variable(node.name)

            if not isinstance(node.value, A.Literal):
                raise DOSCodegenError(
                    "Variable initializers must currently be literals."
                )

            value = node.value.value

            if isinstance(value, bool):
                value = int(value)

            if not isinstance(value, int):
                raise DOSCodegenError(
                    "Only integer and Boolean variable initializers "
                    "are supported in this backend."
                )

            self._check_integer(value)
            self._emit(0xC7, 0x06)
            self._word(self.variables[node.name])
            self._word(value)

            if node.immutable:
                self.constants.add(node.name)
            return

        if isinstance(node, A.Assignment):
            if node.name not in self.variables:
                raise DOSCodegenError(
                    f"Undefined variable: {node.name}"
                )
            if node.name in self.constants:
                raise DOSCodegenError(
                    f"Cannot assign to immutable variable '{node.name}'."
                )

            self._expression(node.value)
            self._emit(0xA3)
            self._word(self.variables[node.name])
            return

        if isinstance(node, A.Output):
            self._output(node.value)
            return

        if isinstance(node, A.Stop):
            self._emit_exit(0)
            return

        if isinstance(node, A.Conditional):
            self._conditional(node)
            return

        if isinstance(node, A.Loop):
            self._loop(node)
            return

        if isinstance(node, A.Import):
            raise DOSCodegenError(
                "Imports are not supported in the DOS v0.1 backend."
            )

        if isinstance(node, A.Function):
            raise DOSCodegenError(
                "Function definitions are not supported by this "
                "DOS backend yet."
            )

        if isinstance(node, A.Return):
            raise DOSCodegenError(
                "'give' requires function-call support, which is "
                "not implemented in this backend yet."
            )

        if isinstance(node, A.Input):
            raise DOSCodegenError(
                "'ask' requires the DOS keyboard-input runtime, "
                "which is not implemented in this backend yet."
            )

        raise DOSCodegenError(
            f"Unsupported DOS statement: {type(node).__name__}"
        )

    def _allocate_variable(self, name):
        if name in self.variables:
            raise DOSCodegenError(
                f"Variable already declared: {name}"
            )

        if self.next_data_address + 2 > 0xFFFF:
            raise DOSCodegenError(
                "DOS variable storage exceeds the 16-bit address space."
            )

        self.variables[name] = self.next_data_address
        self.next_data_address += 2

    def _conditional(self, node):
        else_label = self._new_label("ELSE")
        end_label = self._new_label("ENDIF")

        self._expression(node.condition)

        # OR AX, AX ; JZ else_label
        self._emit(0x09, 0xC0)
        self._rel16((0x0F, 0x84), else_label)

        for statement in node.then_block.statements:
            self._statement(statement)

        self._rel16((0xE9,), end_label)
        self._mark(else_label)

        if node.else_branch is not None:
            if isinstance(node.else_branch, A.Block):
                for statement in node.else_branch.statements:
                    self._statement(statement)
            elif isinstance(node.else_branch, A.Conditional):
                self._conditional(node.else_branch)
            else:
                raise DOSCodegenError(
                    "Unexpected AST node in an else branch."
                )

        self._mark(end_label)

    def _loop(self, node):
        if not isinstance(node.count, A.Literal):
            raise DOSCodegenError(
                "The DOS backend currently requires a literal "
                "integer loop count."
            )

        count = node.count.value
        if isinstance(count, bool) or not isinstance(count, int):
            raise DOSCodegenError(
                "'loop' requires an integer count."
            )
        if count < 0 or count > 32767:
            raise DOSCodegenError(
                "Loop count must be between 0 and 32767."
            )

        if count == 0:
            return

        counter_name = self._new_label("COUNT")
        counter_address = self._allocate_internal_word(counter_name)

        self._emit(0xC7, 0x06)
        self._word(counter_address)
        self._word(count)

        start_label = self._new_label("LOOP")
        end_label = self._new_label("LOOPEND")

        self._mark(start_label)

        # CMP word ptr [counter], 0 ; JE end
        self._emit(0x83, 0x3E)
        self._word(counter_address)
        self._emit(0x00)
        self._rel16((0x0F, 0x84), end_label)

        for statement in node.body.statements:
            self._statement(statement)

        # DEC word ptr [counter] ; JMP start
        self._emit(0xFF, 0x0E)
        self._word(counter_address)
        self._rel16((0xE9,), start_label)

        self._mark(end_label)

    def _allocate_internal_word(self, name):
        if name in self.variables:
            raise DOSCodegenError(
                f"Duplicate internal variable: {name}"
            )

        if self.next_data_address + 2 > 0xFFFF:
            raise DOSCodegenError(
                "DOS variable storage exceeds the 16-bit address space."
            )

        address = self.next_data_address
        self.next_data_address += 2
        self.variables[name] = address
        return address

    # ---------------------------------------------------------
    # Expressions
    # ---------------------------------------------------------

    def _expression(self, node):
        if isinstance(node, A.Literal):
            value = node.value

            if isinstance(value, bool):
                value = int(value)

            if isinstance(value, int):
                self._check_integer(value)
                self._emit(0xB8)
                self._word(value)
                return

            if isinstance(value, str):
                raise DOSCodegenError(
                    "String expressions are not yet supported "
                    "in arithmetic or variable initialization."
                )

            raise DOSCodegenError(
                f"Unsupported literal type: {type(value).__name__}"
            )

        if isinstance(node, A.Name):
            if node.identifier not in self.variables:
                raise DOSCodegenError(
                    f"Undefined variable: {node.identifier}"
                )

            self._emit(0xA1)
            self._word(self.variables[node.identifier])
            return

        if isinstance(node, A.Unary):
            self._expression(node.operand)

            if node.operator == "-":
                # NEG AX
                self._emit(0xF7, 0xD8)
                return

            if node.operator == "+":
                return

            if node.operator == "!":
                true_label = self._new_label("NOTTRUE")
                end_label = self._new_label("NOTEND")

                self._emit(0x09, 0xC0)
                self._rel16((0x0F, 0x84), true_label)

                self._emit(0xB8, 0x00, 0x00)
                self._rel16((0xE9,), end_label)

                self._mark(true_label)
                self._emit(0xB8, 0x01, 0x00)
                self._mark(end_label)
                return

            raise DOSCodegenError(
                f"Unsupported unary operator: {node.operator}"
            )

        if isinstance(node, A.Binary):
            self._binary(node)
            return

        if isinstance(node, A.Call):
            raise DOSCodegenError(
                "Function calls are not supported by the DOS backend yet."
            )

        raise DOSCodegenError(
            f"Unsupported DOS expression: {type(node).__name__}"
        )

    def _binary(self, node):
        op = node.operator

        if op in ("&&", "||"):
            self._logical(node)
            return

        # Preserve the left operand while evaluating the right.
        self._expression(node.left)
        self._emit(0x50)  # PUSH AX
        self._expression(node.right)
        self._emit(0x5B)  # POP BX

        if op == "+":
            self._emit(0x01, 0xD8)  # ADD AX, BX
            return

        if op == "-":
            self._emit(0x93)        # XCHG AX, BX
            self._emit(0x29, 0xD8)  # SUB AX, BX
            return

        if op == "*":
            self._emit(0xF7, 0xEB)  # IMUL BX
            return

        if op in ("/", "%"):
            # Signed division: DX:AX / BX.
            self._emit(0x93)        # XCHG AX, BX
            self._emit(0x99)        # CWD
            self._emit(0xF7, 0xFB)  # IDIV BX

            if op == "%":
                self._emit(0x92)    # XCHG AX, DX
            return

        comparisons = {
            "==": (0x84, 0x85),
            "!=": (0x85, 0x84),
            "<":  (0x8C, 0x8D),
            "<=": (0x8E, 0x8F),
            ">":  (0x8F, 0x8E),
            ">=": (0x8D, 0x8C),
        }

        if op not in comparisons:
            raise DOSCodegenError(
                f"Unsupported binary operator: {op}"
            )

        true_jump, _ = comparisons[op]
        true_label = self._new_label("CMPTRUE")
        end_label = self._new_label("CMPEND")

        # CMP BX, AX
        self._emit(0x39, 0xC3)

        # Conditional jump to true result.
        self._rel16((0x0F, true_jump), true_label)
        self._emit(0xB8, 0x00, 0x00)
        self._rel16((0xE9,), end_label)

        self._mark(true_label)
        self._emit(0xB8, 0x01, 0x00)
        self._mark(end_label)

    def _logical(self, node):
        true_label = self._new_label("LOGTRUE")
        false_label = self._new_label("LOGFALSE")
        end_label = self._new_label("LOGEND")

        self._expression(node.left)
        self._emit(0x09, 0xC0)

        if node.operator == "&&":
            self._rel16((0x0F, 0x84), false_label)
            self._expression(node.right)
            self._emit(0x09, 0xC0)
            self._rel16((0x0F, 0x85), true_label)
            self._rel16((0xE9,), false_label)
        else:
            self._rel16((0x0F, 0x85), true_label)
            self._expression(node.right)
            self._emit(0x09, 0xC0)
            self._rel16((0x0F, 0x85), true_label)
            self._rel16((0xE9,), false_label)

        self._mark(true_label)
        self._emit(0xB8, 0x01, 0x00)
        self._rel16((0xE9,), end_label)

        self._mark(false_label)
        self._emit(0xB8, 0x00, 0x00)

        self._mark(end_label)

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------

    def _output(self, value):
        if isinstance(value, A.Literal) and isinstance(value.value, str):
            self._emit_string(value.value)
            return

        # Evaluate the expression into AX.
        self._expression(value)

        # Call the decimal number formatter.
        self.needs_number_printer = True
        self._rel16((0xE8,), "PRINT_NUMBER")

    def _emit_number_printer(self):
        # Input:
        #   AX = signed 16-bit integer
        #
        # Output:
        #   Prints the integer followed by CR/LF.
        #
        # Preserves BX, CX and DX.
        # Uses DOS interrupt 21h, function 02h.

        self._mark("PRINT_NUMBER")

        # Preserve registers used by the routine.
        self._emit(0x53)              # PUSH BX
        self._emit(0x51)              # PUSH CX
        self._emit(0x52)              # PUSH DX

        # Check whether AX is negative.
        self._emit(0x09, 0xC0)         # OR AX, AX
        self._rel16((0x0F, 0x89), "PRINT_POSITIVE")  # JNS

        # Print the minus sign.
        self._emit(0xB2, ord("-"))     # MOV DL, '-'
        self._emit(0xB4, 0x02)         # MOV AH, 02h
        self._emit(0xCD, 0x21)         # INT 21h

        # Convert to magnitude. 8000h remains 8000h for -32768;
        # unsigned division below handles that magnitude correctly.
        self._emit(0xF7, 0xD8)         # NEG AX

        self._mark("PRINT_POSITIVE")

        # Prepare decimal conversion.
        self._emit(0x31, 0xC9)         # XOR CX, CX
        self._emit(0xBB, 0x0A, 0x00)  # MOV BX, 10

        self._mark("PRINT_DIGIT_DIVIDE")

        # Unsigned AX / 10; quotient -> AX, remainder -> DX.
        self._emit(0x31, 0xD2)         # XOR DX, DX
        self._emit(0xF7, 0xF3)         # DIV BX

        # Save the remainder (one decimal digit).
        self._emit(0x52)              # PUSH DX
        self._emit(0x41)              # INC CX

        # Repeat until the quotient is zero.
        self._emit(0x09, 0xC0)         # OR AX, AX
        self._rel16((0x0F, 0x85), "PRINT_DIGIT_DIVIDE")  # JNZ

        # Digits were pushed least-significant first.
        # Pop them to print in the correct order.
        self._mark("PRINT_DIGIT_OUTPUT")

        self._emit(0x5A)              # POP DX
        self._emit(0x80, 0xC2, 0x30)  # ADD DL, '0'
        self._emit(0xB4, 0x02)         # MOV AH, 02h
        self._emit(0xCD, 0x21)         # INT 21h

        self._emit(0x49)              # DEC CX
        self._rel16((0x0F, 0x85), "PRINT_DIGIT_OUTPUT")  # JNZ

        # Print carriage return and line feed.
        self._emit(0xB2, 0x0D)         # MOV DL, 13
        self._emit(0xB4, 0x02)
        self._emit(0xCD, 0x21)

        self._emit(0xB2, 0x0A)         # MOV DL, 10
        self._emit(0xB4, 0x02)
        self._emit(0xCD, 0x21)

        # Restore registers and return to the caller.
        self._emit(0x5A)              # POP DX
        self._emit(0x59)              # POP CX
        self._emit(0x5B)              # POP BX
        self._emit(0xC3)              # RET

    def _emit_string(self, text):
        if any(ord(ch) > 127 for ch in text):
            raise DOSCodegenError(
                "Only ASCII strings are supported in DOS output."
            )

        # DOS AH=02h prints one character in DL. This avoids the
        # special '$' terminator required by DOS AH=09h.
        for ch in text + "\r\n":
            self._emit(0xB2, ord(ch))  # MOV DL, imm8
            self._emit(0xB4, 0x02)     # MOV AH, 02h
            self._emit(0xCD, 0x21)     # INT 21h

    @classmethod
    def _check_integer(cls, value):
        if not cls.MIN_INTEGER <= value <= cls.MAX_INTEGER:
            raise DOSCodegenError(
                f"Integer {value} is outside the supported signed "
                "16-bit range (-32768 through 32767)."
            )

    # ---------------------------------------------------------
    # MZ executable
    # ---------------------------------------------------------

    @classmethod
    def _make_mz_exe(cls, code):
        # The load module starts after a 32-byte MZ header.
        header_size = cls.HEADER_SIZE

        # Keep the load image paragraph-aligned.
        image = bytearray(code)
        while len(image) % 16:
            image.append(0x90)

        file_size = header_size + len(image)
        pages = (file_size + 511) // 512
        last_page = file_size % 512

        header = struct.pack(
            "<14H",
            0x5A4D,       # MZ signature
            last_page,
            pages,
            0,            # Relocations
            header_size // 16,
            0,            # Minimum extra paragraphs
            0xFFFF,       # Maximum extra paragraphs
            0,            # Initial SS
            0xFFFE,       # Initial SP
            0,            # Checksum
            0,            # Initial IP
            0,            # Initial CS
            0x1C,         # Relocation table offset
            0,            # Overlay
        )

        header += b"\x00" * (header_size - len(header))
        return header + bytes(image)