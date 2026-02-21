---==X Floppy Player X==---
Floppy Player is a lightweight, visual block-based game engine and editor built with Pygame. It allows users to create logic through a drag-and-drop interface inspired by Scratch, featuring a real-time compiler and a custom asset management system.

---=======================================---

-Features:
Visual Block Programming: Drag, drop, and snap blocks together to create complex logic.

Real-time Compilation: Instantly compile your block stacks into executable code via the FloppyCompiler.

Asset Management: Integrated AssetsStorage and FileExplorer to import and manage your sprites and media.

Live Console: Built-in debug console to log messages and monitor program execution.

Custom UI Engine: Includes a specialized font renderer and custom mouse sensitivity handling for a retro-editor feel.

---=======================================---

-Installation:
Prerequisites: Ensure you have Python 3.x and pygame installed.

Bash
pip install pygame
Clone the Repository:

Bash
git clone https://github.com/yourusername/floppy-player.git
cd floppy-player
Run the Editor:

Bash
python editor.py

---=======================================---

-How to Use:
1. The Toolbox
On the left side of the screen, you'll find the Toolbox.

Drag a block from the toolbox onto the canvas to create a new instance.

Scroll through the categories using the mouse wheel or the scrollbar.

Hover over a block to see a description of what it does.

2. Snapping Blocks
Stacking: Drag a block near the bottom of another block to snap them together in a sequence.

Nesting (L-Blocks): Blocks like "Repeat" have a "mouth" where you can place a nested stack of logic.

Inputs (O-Blocks): Round blocks can be dropped into the text slots of other blocks to provide dynamic values.

3. Running Your Project
Click the Play icon (top menu) to compile and run your logic.

If your script is running, the editor UI will hide and your game/logic will execute.

Press ESC to stop execution and return to the editor.

4. Managing Assets
Click the Folder icon to open the Asset Storage. Here you can load local images and files into your project, which can then be referenced by name in your blocks (e.g., Render [mysprite] at [0][0]).

---=======================================---

If you ever need help to do something with a specific block, you can always lay the mouse ontop of a toolbox block for a tip.
This is a school project, but if it does well or if im feeling like it, i may release a full version of the thing, i llok forwar into adding 3D and more optimiziations for low end devices.
You shouldn´t have any problems running this in modern hardware, but maybe it can be a bit heavy for older hardware for i havent optimized my code a lot.
Feel free to give feedback and mod it, if you really want you can help me out in the project. I am not that good in aesthetics and audio production, and even sometimes i get stuck in programming itself.

Made by: Miauwcat14
Contact: miauwcat0@gmail.com
