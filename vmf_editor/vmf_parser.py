
from dataclasses import dataclass, field
import re


BUFFER_SIZE = 4096


@dataclass
class VMFNode:
    name: str
    kind: str
    value: str = ""
    children: list = field(default_factory=list)
    line: int = 0


@dataclass
class VMFDocument:
    root: VMFNode
    errors: list = field(default_factory=list)
    encoding: str = "utf-8"


class VMFParser:

    PAIR_PATTERN = re.compile(
        r'^"((?:\\.|[^"])*)"\s+"((?:\\.|[^"])*)"$'
    )

    def __init__(self):

        self.line_index = 0
        self.stack = []
        self.pending_name = None
        self.errors = []

        self.root = VMFNode(
            name="root",
            kind="block"
        )

        self.stack.append(self.root)

    def detect_encoding(self, file_path):

        with open(file_path, "rb") as file:
            sample = file.read(65536)

        if sample.startswith(b"\xff\xfe"):
            return "utf-16-le"

        if sample.startswith(b"\xfe\xff"):
            return "utf-16-be"

        try:
            sample.decode("utf-8-sig")
            return "utf-8-sig"

        except UnicodeDecodeError:
            return "cp1251"

    def remove_comment(self, line):

        quoted = False
        escaped = False

        for i, char in enumerate(line):

            if escaped:
                escaped = False
                continue

            if char == "\\" and quoted:
                escaped = True
                continue

            if char == '"':
                quoted = not quoted
                continue

            if not quoted and line[i:i+2] == "//":
                return line[:i]

        return line

    def parse_line(self, line):

        self.line_index += 1

        line = self.remove_comment(line).strip()

        if not line:
            return

        # START BLOCK

        if line == "{":

            if self.pending_name is None:

                self.errors.append(
                    f"Line {self.line_index}: Unknown block name"
                )

                return

            node = VMFNode(
                name=self.pending_name,
                kind="block",
                line=self.line_index
            )

            self.stack[-1].children.append(node)
            self.stack.append(node)

            self.pending_name = None
            return

        # END BLOCK

        if line == "}":

            if len(self.stack) > 1:
                self.stack.pop()

            else:
                self.errors.append(
                    f"Line {self.line_index}: Unexpected closing bracket"
                )

            self.pending_name = None
            return

        # KEY-VALUE

        match = self.PAIR_PATTERN.match(line)

        if match:

            name, value = match.groups()

            node = VMFNode(
                name=name,
                kind="value",
                value=value,
                line=self.line_index
            )

            self.stack[-1].children.append(node)

            self.pending_name = None
            return

        # BLOCK NAME

        self.pending_name = line

    def parse(self, file_path):

        self.__init__()

        encoding = self.detect_encoding(file_path)

        try:
            with open(
                file_path,
                "r",
                encoding=encoding,
                buffering=BUFFER_SIZE
            ) as file:

                for line in file:
                    self.parse_line(line)

        except (OSError, UnicodeError) as error:
            self.errors.append(str(error))

        if self.pending_name is not None:
            self.errors.append(
                f"Line {self.line_index}: "
                f"Block without opening bracket: {self.pending_name}"
            )

        if len(self.stack) > 1:
            self.errors.append(
                f"Unclosed blocks: {len(self.stack) - 1}"
            )

        return VMFDocument(
            root=self.root,
            errors=self.errors.copy(),
            encoding=encoding
        )
