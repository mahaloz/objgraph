# objgraph
Convert an objdump output into a CFG via Binary Ninja

## Installation
Copy this entire repo in your Binary Ninja plugins directory. For me this looks like:
```bash
cp -r  ../objgraph  "/Users/mahaloz/Library/Application\ Support/Binary\ Ninja/plugins/"
```

It will look a little different on Linux.

## Usage
The power of this plugin comes from its quickness to create a working CFG from objdump output. You could always 
write an entire lifting plugin for an arch in binja, or instead you could use this plugin which does nothing but
make a CFG. When quickly adding an arch the easiest and fastest way is to copy `generic_arch` found in the `archs` 
folder. Copy the file, change the `name` in the class and define the regex needed for a branching instruction. 
All that is needed for any arch to work is that you define how branching can be regexed:

```python
def get_instruction_info(self, data, addr):
    instr_len = 4
    result = InstructionInfo()
    result.length = instr_len

    instr_txt: str = get_instr(addr)
    if not instr_txt:
        return None
    
    # LM32 example:
    # bgeu r11,r1,40007194 <encrypt+0xb8>
    if instr_txt.startswith("b"):
        dest = int(instr_txt.split(" ")[1].split(",")[2], 16)
        result.add_branch(BranchType.TrueBranch, self.rebase_addr(dest, up=False))
        result.add_branch(BranchType.FalseBranch, addr + instr_len)
```

Feel free to not redfine the stack pointer, registers, or anything else. After completing
your implementation, just place it in the `archs` folder and select it in the config box
dialog found in the `Tools` tab in Binary Ninja. Make sure your arch class name ends in 
`Arch`.

### Using cache

Instead of running objdump and readelf on each run, you can instead make an output file
of the contents into `prog_name.readelf` and `prog_name.objdump`, where `prog_name` is 
the program you are analyzing. 
```bash
readelf -s prog_name > prog_name.readelf && \
objdump -D -M intel prog_name > prog_name.objdump
```

## Example

As an example, you can see the `LM32` arch from `hitbpro-2021` ctf. Open the `firmware.exe` binary in 
Binary Ninja. Go to the tools tab, then click `Objgraph: Configure`. Make the binutils folder the
`./examples/lm32` folder found in this repo. Check `use dumpfile` avoid running the readelf and objdump
binaries, since I ran them and left the output in the same dir.

![](./assets/objgraph_demo.png)

## Future Work

This plugin can actually be simplified a little more. It could actually be updated to take just a `config.json` file
to allow you to more easily define regexs without writing python code. I leave this to future work. Yeet.



