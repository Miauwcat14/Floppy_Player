import json
import os
import pygame
from block_code import OPCODES

class FloppyCompiler:
    def __init__(self, screen, assets):
        # We use 'ctx' as our 'Virtual Machine' state
        self.ctx = {
            'screen': screen,
            'assets': assets, 
            'vars': {},
            'running': False
        }
        self.executable_list = []

    def load_project(self, floppy_file):
        """
        Reads the .floppy JSON file and assembles the C++ optimized function list.
        """
        if not os.path.exists(floppy_file):
            print(f"Error: {floppy_file} not found.")
            return

        with open(floppy_file, 'r') as f:
            data = json.load(f)
        
        # This converts the data into 'live' executable logic
        self.executable_list = self._assemble(data)
        self.ctx['running'] = True

    def _assemble(self, data_list):
        tasks = []
        for item in data_list:
            cmd = item["cmd"]
            args = item["args"]

            if cmd in OPCODES:
                logic_func = OPCODES[cmd]
                
                if item.get("type") == "l": # Handle Nesting (L-Blocks)
                    substack = self._assemble(item["substack"])
                    
                    if cmd == "If":
                        def if_task(s=substack, a=args):
                            from block_code import checkifvar
                            # This is the secret sauce: 
                            # checkifvar runs the 'key_pressed' function for us!
                            condition_result = checkifvar(a, 0, self.ctx)
                            
                            if condition_result: # If it's 1 or True
                                for step in s: step()
                        tasks.append(if_task)
                    else:
                        # Existing Repeat/Loop logic
                        def loop_task(s=substack, a=args):
                            from block_code import checkifvar
                            count = int(checkifvar(a, 0, self.ctx))
                            for _ in range(count):
                                for step in s: step()
                        tasks.append(loop_task)
                else:
                    # Standard block closure (Move, Print, etc.)
                    def task(f=logic_func, a=args):
                        f(self.ctx, a)
                    tasks.append(task)
        return tasks

    def run_frame(self):
        if self.ctx['running']:
            try:
                for task in self.executable_list:
                    task()
            except Exception as e:
                self.ctx['running'] = False
                # This uses your new console to show the error in-game!
                if 'console' in self.ctx:
                    self.ctx['console'].log(f"SYS-ERROR: {str(e)}", (255, 50, 50))
                    self.ctx['console'].active = True
    
    def compile(self, start_block):
        """Directly converts Block objects into executable functions."""
        # Convert the visual block chain into the intermediate dictionary format
        data = []
        curr = start_block
        while curr:
            if curr.btype == "o":  # If it's an O-block in the main chain, skip it
                curr = curr.child
                continue
                
            block_data = {
                "cmd": curr.text.split('[')[0].strip(),
                "args": curr.get_slot_values(), # This handles the nested O-blocks correctly
                "type": curr.btype,
                "substack": []
            }
            # If it's a loop, recursively get the inside blocks
            if curr.btype == "l" and curr.nested_child:
                block_data["substack"] = self._get_substack_data(curr.nested_child)
            
            data.append(block_data)
            curr = curr.child
            
        self.executable_list = self._assemble(data)

    def _get_substack_data(self, block):
        """Helper to convert nested blocks to dictionary format."""
        nodes = []
        curr = block
        while curr:
            nodes.append({
                "cmd": curr.text.split('[')[0].strip(),
                "args": curr.get_slot_values(),
                "type": curr.btype,
                "substack": self._get_substack_data(curr.nested_child) if curr.nested_child else []
            })
            curr = curr.child
        return nodes