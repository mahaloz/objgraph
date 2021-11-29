#!/usr/bin/env python3
#
# To use this file fast and efficiently, only edit things
# marked with an: ###EDITME.
#

from binaryninja.architecture import Architecture
from binaryninja.function import RegisterInfo, InstructionInfo, InstructionTextToken
from binaryninja.enums import InstructionTextTokenType, BranchType
import re

from ..objgraph import get_instr


class ObjgraphArch(Architecture):
    # ========= EDITME ========== #
    name = 'ObjgraphArch'
    address_size = 4
    default_int_size = 4
    instr_alignment = 1
    max_instr_length = 4
    # =========================== #

    regs = {
        'SP': RegisterInfo('SP', 4),
    }
    stack_pointer = "SP"

    #
    # utils
    #

    def rebase_addr(self, addr, up=True):
        if up:
            return addr + 0x40000000 - 120
        else:
            return addr - 0x40000000 + 120

    #
    # public
    #

    def get_instruction_info(self, data, addr):
        instr_len = 4
        result = InstructionInfo()
        result.length = instr_len

        instr_txt: str = get_instr(addr)
        if not instr_txt:
            return None

        # ========= EDITME =========== #
        # Edit this section to parse a branching instruction
        # so we can know how to craft control flow on a
        # branch.

        if instr_txt.startswith("b"):
            dest = int(instr_txt.split(" ")[1].split(",")[2], 16)
            result.add_branch(BranchType.TrueBranch, self.rebase_addr(dest, up=False))
            result.add_branch(BranchType.FalseBranch, addr + instr_len)
        elif "ret" in instr_txt:
            result.add_branch(BranchType.FunctionReturn)
        # ============================ #

        return result

    def get_instruction_text(self, data, addr):
        instr_txt = self.get_instr(addr)
        if not instr_txt:
            return None

        result = []
        atoms = [t for t in re.split(r'([, ()\+-])', instr_txt) if t]
        result.append(InstructionTextToken(InstructionTextTokenType.InstructionToken, atoms[0]))
        if atoms[1:]:
            result.append(InstructionTextToken(InstructionTextTokenType.TextToken, ' '))

        for atom in atoms[1:]:
            if not atom or atom == ' ':
                continue

            elif len(re.findall(r"[0-9a-fA-F]{8,16}", atom)) > 0:
                rebased_addr = self.rebase_addr(int(atom, 16), up=False)
                result.append(
                    InstructionTextToken(InstructionTextTokenType.PossibleAddressToken, hex(rebased_addr), rebased_addr)
                )
            elif atom.isdigit():
                result.append(InstructionTextToken(InstructionTextTokenType.IntegerToken, atom, int(atom)))
            elif atom == '(':
                result.append(InstructionTextToken(InstructionTextTokenType.BeginMemoryOperandToken, atom))
            elif atom == ')':
                result.append(InstructionTextToken(InstructionTextTokenType.EndMemoryOperandToken, atom))
            elif atom in ['+', '-']:
                result.append(InstructionTextToken(InstructionTextTokenType.TextToken, atom))
            elif atom == ',':
                result.append(InstructionTextToken(InstructionTextTokenType.OperandSeparatorToken, atom))
            elif atom.startswith("<"):
                result.append(InstructionTextToken(InstructionTextTokenType.TextToken, " " + atom))
            else:
                result.append(InstructionTextToken(InstructionTextTokenType.TextToken, atom))

        return result, 4

    def get_instruction_low_level_il(self, data, addr, il):
        return None


ObjgraphArch.register()
