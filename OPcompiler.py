import json
import os
import pygame
from block_code import OPCODES

class FloppyCompiler:
    def __init__(self, screen, assets):
        self.ctx = {
            'screen': screen,
            'assets': assets,
            'mouse': None,
            'vars': {},
            'dt': 0,
            'running': False,
            'finished': False,
            'pc': 0,
            'sleep_until': 0,
            'rgb': (255, 255, 255)
        }
        self.executable_list = []

    def run_once(self):
        """Executes blocks safely, catching any crashes."""
        if self.ctx.get('finished', False): return

        try:
            # Check for non-blocking wait
            if pygame.time.get_ticks() < self.ctx.get('sleep_until', 0):
                return 

            pc = self.ctx.get('pc', 0)
            if pc < len(self.executable_list):
                task = self.executable_list[pc]
                self.ctx['pc'] = pc + 1
                task()
            else:
                self.ctx['finished'] = True
                # Use .log() if it's a class, or .append() if it's a list
                self._safe_log("--- Script Finished ---")
                self._safe_log("Press ESC to exit...")
        
        except Exception as e:
            error_msg = f"CRASH: {str(e)}"
            self._safe_log(error_msg)
            self.ctx['finished'] = True

    def _safe_log(self, msg):
        console = self.ctx.get('console')
        if hasattr(console, 'active'):
            console.active = True
            console.log(msg)
        elif isinstance(console, list):
            console.append(msg)

    def load_project(self, floppy_file):
        if not os.path.exists(floppy_file):
            print(f"Error: {floppy_file} not found.")
            return

        with open(floppy_file, 'r') as f:
            data = json.load(f)
        self.executable_list = self._assemble(data)
        self.ctx['running'] = True

    def _assemble(self, data_list):
        tasks = []
        for item in data_list:
            cmd = item["cmd"]
            args = item["args"]
            print(f"[Compiler] Assembling: {cmd} with args: {args}")

            if cmd in OPCODES:
                logic_func = OPCODES[cmd]
                
                if item.get("type") == "l":
                    substack = self._assemble(item["substack"])
                    
                    if cmd == "If":
                        def if_task(s=substack, a=args):
                            from block_code import checkifvar
                            # Evaluate the condition
                            condition = bool(checkifvar(a, 0, self.ctx))
                            
                            if condition:
                                # Run everything inside the 'If' block immediately
                                for task_func in s:
                                    task_func()
                                    
                        tasks.append(if_task)
                        
                    elif cmd == "For Each":
                        def foreach_task(s=substack, a=args):
                            from block_code import checkifvar
                            # Slots: For Each [i] in [bullets]
                            # a[0] is "i", a[1] is "bullets"
                            var_name = str(a[0])
                            list_name = str(a[1])
                            
                            target_list = self.ctx["vars"].get(list_name, [])
                            if isinstance(target_list, list):
                                for val in target_list:
                                    self.ctx["vars"][var_name] = val # Update 'i'
                                    for step in s: step()
                        tasks.append(foreach_task)
                        
                    elif cmd == "Repeat":
                        def loop_task(s=substack, a=args):
                            from block_code import checkifvar
                            count = int(checkifvar(a, 0, self.ctx))
                            
                            # We don't use a 'for' loop here! 
                            # We inject the substack blocks back into the main list 
                            # so the 'pc' can walk through them one by one.
                            
                            # This is advanced: we are effectively 'unrolling' the loop
                            new_tasks = []
                            for _ in range(count):
                                new_tasks.extend(s)
                                
                            # Insert these tasks right after the current block
                            current_pc = self.ctx.get('pc', 0)
                            for i, t in enumerate(new_tasks):
                                self.executable_list.insert(current_pc + i, t)
                                
                        tasks.append(loop_task)
                    elif cmd == "While":
                        def while_task(s=substack, a=args):
                            from block_code import checkifvar
                            
                            #NO LIMITE! If this is infinite, the game freezes. Skill issue! :P
                            while bool(checkifvar(a, 0, self.ctx)):
                                for task_func in s:
                                    task_func()
                                    
                        tasks.append(while_task)
                    elif cmd == "Forever while":
                        start_pc = len(tasks) # Remember where the loop starts
                        
                        def while_task(a=args, s=substack, loop_start=start_pc):
                            from block_code import checkifvar
                            condition = bool(checkifvar(a, 0, self.ctx))
                            
                            if condition:
                                # Instead of a loop, we just 'inject' the substack 
                                # into the execution queue for the next frames.
                                # OR better: run them and move the PC back.
                                for task_func in s:
                                    task_func()
                                
                                # This is the magic: set the Program Counter back to this block
                                # so it runs again on the NEXT frame call!
                                self.ctx['pc'] -= 1 
                                
                        tasks.append(while_task)
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
        self.executable_list = [] 
        self.ctx['pc'] = 0              # Reset to block 0
        self.ctx['finished'] = False    # Un-finish the engine
        self.ctx['sleep_until'] = 0     # Clear any pending waits
        self.ctx['vars'] = {}

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