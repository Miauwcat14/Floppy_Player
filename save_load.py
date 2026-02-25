import json

def save_project(blocks, filename="my_game.floppy"):
    # Only save 'root' blocks (blocks that aren't attached to anything above them)
    root_blocks = [b for b in blocks if b.parent is None and b.nested_parent is None]
    
    serialized_data = []
    for b in root_blocks:
        serialized_data.append(block_to_dict(b))
        
    with open(filename, "w") as f:
        json.dump(serialized_data, f, indent=4)

def block_to_dict(b):
    return {
        "text": b.text,
        "pos": b.pos,
        "btype": b.btype,
        "child": block_to_dict(b.child) if b.child else None,
        "nested": block_to_dict(b.nested_child) if b.nested_child else None
    }

def load_project(filename, editor_instance):
    with open(filename, "r") as f:
        data = json.load(f)
    
    new_blocks = []
    for block_data in data:
        new_blocks.append(dict_to_block(block_data, editor_instance))
    return new_blocks

def dict_to_block(data, editor):
    # 1. Create the block
    # Note: Make sure the Block class knows how to handle the color from the text/template!
    b = Block(data['text'], data['pos'], data['btype'], editor.mouse)
    
    # 2. Re-link Child (The block snapped underneath)
    if data['child']:
        child_block = dict_to_block(data['child'], editor)
        b.child = child_block
        child_block.parent = b
        # Force the child to snap to the parent's bottom immediately
        child_block.pos = [b.pos[0], b.pos[1] + b.height]
        
    # 3. Re-link Nested (The block inside a loop)
    if data['nested']:
        nested_block = dict_to_block(data['nested'], editor)
        b.nested_child = nested_block
        nested_block.nested_parent = b
        
    # 4. CRITICAL: Refresh the block so it realizes it has children
    # This ensures 'height' is updated correctly for the next blocks in the chain
    if hasattr(b, 'update'):
        b.update() 
        
    return b