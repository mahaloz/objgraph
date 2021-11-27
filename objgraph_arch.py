#!/usr/bin/env python3

from binaryninja.log import log_info
from binaryninja.architecture import Architecture
from binaryninja.function import RegisterInfo, InstructionInfo, InstructionTextToken
from binaryninja.enums import InstructionTextTokenType, BranchType
import re


def objdump_data():
    dis_file = "/Users/mahaloz/hitb-21/challenges/hsm/plugin/firmware.diss"
    with open(dis_file, "r") as fp:
        data = fp.read()

    regex = r"([0-9,a-f]{8}):\t([0-9,a-f]{2} ){4}\t(.*)"
    out = re.findall(regex, data)
    lines = {int(o[0], 16): o[2] for o in out}
    return lines


class ObjgraphArch(Architecture):
    name = 'ObjgraphArch'

    address_size = 4
    default_int_size = 4
    instr_alignment = 1
    max_instr_length = 4

    lines = objdump_data()

    #
    # utils
    #

    def rebase_addr(self, addr, up=True):
        if up:
            return addr + 0x40000000 - 120
        else:
            return addr - 0x40000000 + 120

    def get_instr(self, addr):
        val = self.rebase_addr(addr)

        try:
            return self.lines[val]
        except KeyError:
            return None

    #
    # public
    #

    def get_instruction_info(self, data, addr):
        instr_len = 4
        result = InstructionInfo()
        result.length = instr_len

        instr_txt: str = self.get_instr(addr)
        if not instr_txt:
            return None

        # bgeu r11,r1,40007194 <encrypt+0xb8>
        if "bgeu " in instr_txt:
            dest = int(instr_txt.split(" ")[1].split(",")[2], 16)
            result.add_branch(BranchType.TrueBranch, self.rebase_addr(dest, up=False))
            result.add_branch(BranchType.FalseBranch, addr + instr_len)
        elif "ret" in instr_txt:
            result.add_branch(BranchType.FunctionReturn)

        return result

    def get_instruction_text(self, data, addr):
        instr_txt = self.get_instr(addr)
        if not instr_txt:
            return None

        tokens = [InstructionTextToken(InstructionTextTokenType.TextToken, instr_txt)]
        return tokens, 4

    def get_instruction_low_level_il(self, data, addr, il):
        return None


ObjgraphArch.register()
