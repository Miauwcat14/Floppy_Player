import json
import os
import pygame
from block_code import *
from profiler import EngineProfiler

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
        self.profiler = EngineProfiler()
        self.ctx['profiler'] = self.profiler

    def run_once(self):
        if self.ctx.get('finished', False): return

        try:
            if pygame.time.get_ticks() < self.ctx.get('sleep_until', 0):
                return 

            pc = self.ctx.get('pc', 0)
            if pc >= len(self.executable_list):
                self.ctx['finished'] = True
                self._safe_log("--- Script Finished ---")
                self._safe_log("Press ESC to exit...")
                self.profiler.export()
                return
            if pc < len(self.executable_list):
                task = self.executable_list[pc]
                self.ctx['pc'] = pc + 1
                task()
        
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
                            condition = bool(checkifvar(a, 0, self.ctx))
                            
                            if condition:
                                for task_func in s:
                                    task_func()
                                    
                        tasks.append(if_task)
                        
                    elif cmd == "For Each":
                        def foreach_task(s=substack, a=args):
                            from block_code import checkifvar
                            var_name = str(a[0])
                            list_name = str(a[1])
                            
                            target_list = self.ctx["vars"].get(list_name, [])
                            if isinstance(target_list, list):
                                for val in target_list:
                                    self.ctx["vars"][var_name] = val
                                    for step in s: step()
                        tasks.append(foreach_task)
                        
                    elif cmd == "Repeat":
                        def loop_task(s=substack, a=args):
                            from block_code import checkifvar
                            count = int(checkifvar(a, 0, self.ctx))
                            new_tasks = []
                            for _ in range(count):
                                new_tasks.extend(s)
                            current_pc = self.ctx.get('pc', 0)
                            for i, t in enumerate(new_tasks):
                                self.executable_list.insert(current_pc + i, t)
                        tasks.append(loop_task)
                    elif cmd == "While":
                        requires_safe = self._substack_requires_scheduler(item["substack"])

                        if not requires_safe:
                            def fast_while(s=substack, a=args):
                                from block_code import checkifvar

                                loop_name = f"While@{id(s)}"
                                self.profiler.start_loop(loop_name)

                                while bool(checkifvar(a, 0, self.ctx)):
                                    self.profiler.tick_loop()

                                    sub_start = self.profiler.start_substack()
                                    for task_func in s:
                                        task_func()
                                    self.profiler.end_substack(sub_start)

                                self.profiler.end_loop()
                            tasks.append(fast_while)

                        else:
                            start_pc = len(tasks)

                            def safe_while(a=args, s=substack, loop_start=start_pc):
                                from block_code import checkifvar

                                if bool(checkifvar(a, 0, self.ctx)):
                                    for task_func in s:
                                        task_func()
                                    self.ctx['pc'] -= 1

                            tasks.append(safe_while)
                    elif cmd == "Forever while":

                        def while_task(a=args, s=substack):
                            from block_code import checkifvar
                            condition = bool(checkifvar(a, 0, self.ctx))
                            if condition:
                                for task_func in s:
                                    task_func()
                                self.ctx['pc'] -= 1

                        tasks.append(while_task)
                else:
                    def task(f=logic_func, a=args, name=cmd):
                        start = self.profiler.start_opcode(name)
                        f(self.ctx, a)
                        self.profiler.end_opcode(name, start)
                    tasks.append(task)
        return tasks

    def run_frame(self):
        if self.ctx['running']:
            try:
                for task in self.executable_list:
                    task()
            except Exception as e:
                self.ctx['running'] = False
                if 'console' in self.ctx:
                    self.ctx['console'].log(f"SYS-ERROR: {str(e)}", (255, 50, 50))
                    self.ctx['console'].active = True
    
    def compile(self, start_block):
        self.executable_list = [] 
        self.ctx['pc'] = 0
        self.ctx['finished'] = False
        self.ctx['sleep_until'] = 0
        self.ctx['vars'] = {}

        data = []
        curr = start_block
        while curr:
            if curr.btype == "o":
                curr = curr.child
                continue
                
            block_data = {
                "cmd": curr.text.split('[')[0].strip(),
                "args": curr.get_slot_values(),
                "type": curr.btype,
                "substack": []
            }
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
    
    def _substack_requires_scheduler(self, data_list):
        for item in data_list:
            if item["cmd"] in SCHEDULER_DEPENDENT:
                return True
            if item.get("substack"):
                if self._substack_requires_scheduler(item["substack"]):
                    return True
        return False