#!/usr/bin/env python3

print("TODO: To be implemented")


exit

"""

Please implement python script, 
keep description and specification I provide you at a top of the file in comment
clearly annotated for future file editors to be kept and updated as script evolves,
in structured way with short reusable functions,
in a way that can be imported by other python3 scripts and used as library.
Tool can use `jq` external commandline tool, whenever appropriate to simplify codecase.

When used from command line.
the more -v|--verbose flag used the more verbose it becomes,
and verbosity logging is prefixed 'INFO:' 'DEBUG:' 'WARNING:' 'ERROR:' and goes to STDERR.

We like an utility that would allow working
with chromium bookmarks json file standard
(chromium, chrome, brave, etc).

We want to support usecase of users that use default data directory
and multiple profiles,
as well as users who set custom --user-data-dir= chromium/chrome base directory.

For now we would like to be able to :

* list bookmark directories paths 
   * In different formats : in format similar to `find` with `/` , also with option to display `id` next to each at the end, or just as csv with id, parentid, and name..., jsonl (jsonlines)
   * displaying such three without or with bookmarks themselves
   * possibility to start at selected subtree
* list contents of some bookmark folder (bookmarks and folders, or just bookmarks, or just folders...)
   * also in different formats (just urls, or urls and titles, or as jsonl, or as markdown)
* as "selector" for selecting directory user should be able to use either id or name or fragment of foldername (and in case of ambiguity get 'ERROR: ambiguous bookmark folder selector, expected one folder to match while all those folders match: ... .

Prepare structurally codebase for future were new features will be added, and keep in project description list notes as future roadmap:

* features for modyfing bookmarks:
  * moving bookmark between folders
  * merging bookmark folders
  * searching for duplicates
  * adding bookmarks
  * editing bookmark (title, url, etc) or folder
  * syncing bookmarks between browsers
  * import/export of bookmarks to other formars, files, maybe tracking in sqlite3, especially for meta menagement of bookmarks from multple browsers

---

HERE are extra notes from assistant that may help you implement it:

https://www.perplexity.ai/search/bookmarks-sqlite-of-chromium-c-_2mYTGT3QcyWsGSZMBbS9Q

# Understanding and Manipulating Chrome/Chromium/Brave Bookmarks Programmatically

Chrome, Chromium, and Brave browsers all use the same underlying bookmarking system as they share the Chromium codebase. Despite what many users might assume, bookmarks in these browsers are not stored in SQLite format but rather in a JSON file. This report explores the structure, storage format, and programmatic manipulation of bookmarks in these browsers.

## Bookmark Storage Format and Location

Contrary to the query's assumption, bookmarks in Chromium-based browsers are stored in a JSON file, not a SQLite database. The location varies by browser and operating system:

### Chrome
- Windows: `C:\Users$$USERNAME]\AppData\Local\Google\Chrome\User Data\Default\Bookmarks`
- Linux: `~/.config/google-chrome/Default/Bookmarks`

### Brave
- Windows: `C:\Users$$USERNAME]\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Bookmarks`[5][10]
- Linux: Similar to Chrome but in the Brave directory

### Chromium
- Linux: `~/.config/chromium/Default/Bookmarks`[16]

You can locate the Chromium bookmarks file on Linux with:
```bash
find ~/.config/chromium -type f -name Bookmarks
```

## Bookmark Data Structure

Bookmarks are organized in a hierarchical tree structure where each node is either a bookmark or a folder. The JSON file contains all information about bookmark names, URLs, organization, and display order.

### Root Structure

The bookmarks JSON file has several key components:
- A `checksum` element for file integrity
- A `roots` element containing the entire bookmarks tree structure[13]

### Special Folders

Several special folders exist in the bookmarks structure:
- `bookmark_bar`: The folder displayed at the top of the browser window (Bookmarks Bar)[14]
- `other`: Bookmarks displayed in the full list (Other Bookmarks)[14][15]
- `mobile`: Bookmarks for mobile devices[14]
- `managed`: Bookmarks configured by system administrators[14]

### Node Structure

#### Folder Node
```json
{
  "date_added": "13296231151797274",
  "guid": "f9f7a06b-7b14-43b0-8f22-cb79a8188670",
  "id": "32",
  "name": "My Folder",
  "type": "folder",
  "children": [...]
}
```

#### Bookmark Node
```json
{
  "date_added": "13296231151797274",
  "date_last_used": "0",
  "guid": "307be193-6fb0-41a7-9c10-ef3320b8a98b",
  "id": "85",
  "name": "Example Bookmark",
  "type": "url",
  "url": "https://example.com"
}
```

## Display Order and Hierarchy

The display order of bookmarks and folders is determined by their position in the JSON tree:

1. The order of bookmark nodes within the `children` array of a folder determines the display order[14]
2. The hierarchical structure is represented through nested `children` arrays
3. Each bookmark node has an `id` property that uniquely identifies it
4. The parent-child relationship is implicit in the JSON structure

## Programmatic Manipulation (Python on Linux)

Since bookmarks are stored in a JSON file, you can manipulate them using Python's json module:

### Reading Bookmarks

```python
import json
import os

# Get bookmarks file path (Chromium example)
bookmarks_path = os.path.expanduser('~/.config/chromium/Default/Bookmarks')

# Load the bookmarks
with open(bookmarks_path, 'r', encoding='utf-8') as f:
    bookmarks_data = json.load(f)
```

### Finding a Folder by Name

```python
def find_folders_by_name(node, folder_name, path=None, results=None):
    """Recursively find folders with given name and return their IDs and paths"""
    if path is None:
        path = []
    if results is None:
        results = []

    current_path = path.copy()

    if node.get('type') == 'folder' and node.get('name') == folder_name:
        results.append({
            'id': node.get('id'),
            'guid': node.get('guid'),
            'path': current_path
        })

    # Add current node to path for children
    if 'name' in node:
        current_path.append(node['name'])

    # Recursively search children
    if 'children' in node:
        for child in node['children']:
            find_folders_by_name(child, folder_name, current_path, results)

    return results

# Usage
folders = []
for root_name, root_folder in bookmarks_data['roots'].items():
    if isinstance(root_folder, dict):
        folders.extend(find_folders_by_name(root_folder, "My Folder", [root_name]))
```

### Listing Folders and Bookmarks in a Folder

```python
def get_folder_contents(node):
    """Get folders and bookmarks in a node"""
    if node.get('type') != 'folder' or 'children' not in node:
        return [], []

    folders = []
    bookmarks = []

    for child in node['children']:
        if child.get('type') == 'folder':
            folders.append(child)
        elif child.get('type') == 'url':
            bookmarks.append(child)

    return folders, bookmarks
```

### Finding Node by ID

```python
def find_node_by_id(node, node_id, path=None):
    """Find a node by its ID and return the node and its path"""
    if path is None:
        path = []

    current_path = path.copy()

    if node.get('id') == node_id:
        return node, current_path

    if 'name' in node:
        current_path.append(node['name'])

    if 'children' in node:
        for child in node['children']:
            result, result_path = find_node_by_id(child, node_id, current_path)
            if result:
                return result, result_path

    return None, []
```

### Adding a Bookmark

```python
def add_bookmark(parent_node, name, url):
    """Add a new bookmark to a parent folder node"""
    import time

    # Chrome timestamp is microseconds since Jan 1, 1601
    timestamp = str(int(time.time() * 1000000 + 11644473600000000))

    # Create a new bookmark
    new_bookmark = {
        "date_added": timestamp,
        "guid": str(uuid.uuid4()),  # Requires import uuid
        "id": str(max_id + 1),  # You need to determine the max ID in the tree first
        "name": name,
        "type": "url",
        "url": url
    }

    # Add to parent's children
    if 'children' not in parent_node:
        parent_node['children'] = []

    parent_node['children'].append(new_bookmark)
    return new_bookmark
```

### Updating a Bookmark

```python
def update_bookmark_name(node, bookmark_id, new_name):
    """Update the name of a bookmark"""
    bookmark_node, _ = find_node_by_id(node, bookmark_id)
    if bookmark_node and bookmark_node.get('type') == 'url':
        bookmark_node['name'] = new_name
        return True
    return False

def move_bookmark(node, bookmark_id, new_parent_id):
    """Move a bookmark to a different folder"""
    # Find the bookmark and its current parent
    bookmark_node = None
    current_parent = None

    # (This would require a more complex search function to find both the node and its parent)
    # Then remove from current parent and add to new parent

    # Code would:
    # 1. Find the bookmark node
    # 2. Find its current parent
    # 3. Find the new parent
    # 4. Remove from current parent's children
    # 5. Add to new parent's children
```

### Saving Changes

```python
def save_bookmarks(bookmarks_data, bookmarks_path):
    """Save the updated bookmarks JSON"""
    # Create a backup first
    import shutil
    shutil.copy2(bookmarks_path, bookmarks_path + '.bak')

    # Write the updated file
    with open(bookmarks_path, 'w', encoding='utf-8') as f:
        json.dump(bookmarks_data, f, indent=4)
```

## Implementation Considerations

When manipulating the bookmarks file:

1. **Always create a backup** before modifications
2. **Maintain ID uniqueness** when adding new nodes
3. **Preserve the file structure** including the checksum property
4. **Close the browser** before modifying its bookmarks file
5. Pay attention to the **"ID" property** of each entity when editing[9]

The browser reads the JSON file directly to populate the bookmarks interface, so the structure must be maintained precisely. Changes are not automatically picked up by a running browser; you'll need to restart the browser after modifying the file.

## Alternatives for Bookmark Manipulation

1. **Chrome Extension API**: For more reliable and supported bookmark manipulation, consider using the Chrome Extensions API[17]
2. **Registry Managed Bookmarks**: In Windows environments, managed bookmarks can be deployed via registry entries[1][2]
3. **Export/Import Workflow**: For backup and migration, use the browser's built-in export/import features[6][8]

By understanding the structure of the bookmarks JSON file, you can create powerful tools to manage, analyze, and manipulate your browser bookmarks programmatically.


# Programmatic Manipulation of Chromium-Based Browser Bookmarks Using `jq`

## Introduction
Chromium-based browsers (Chrome, Brave, Chromium) store bookmarks in a JSON file rather than SQLite databases. This structural choice enables powerful manipulation using JSON processing tools like `jq`. This report demonstrates how to achieve bookmark management tasks through `jq` commands, addressing both read operations and complex updates while maintaining data integrity.

---

## I. Bookmark File Structure Analysis
The `Bookmarks` file uses a nested JSON structure with several key components:

### 1.1 Root Elements
```json
{
  "checksum": "...",
  "roots": {
    "bookmark_bar": {...},
    "other": {...},
    "mobile": {...}
  }
}
```
The hierarchical organization emerges through nested `children` arrays[13][14].

### 1.2 Node Types
- **Folders**: Contain `type: "folder"` and `children` array
- **URLs**: Contain `type: "url"` with `url` property
- Metadata includes `id`, `guid`, and `date_added`[13][14]

---

## II. Read Operations with `jq`

### 2.1 Fetch Directory ID by Name
```bash
jq '.roots.bookmark_bar | .. | select(.type? == "folder" and .name == "Research") | {id, parentId}' Bookmarks
```
This recursive search:
1. Starts at bookmarks bar
2. Traverses all nodes (`..`)
3. Filters folders with target name
4. Returns IDs[13][14]

### 2.2 Hierarchy Reconstruction
```bash
jq -r '
  def path($node):
    if $node.parentId then path(.roots | .. | select(.id? == $node.parentId)) + "/" + $node.name
    else $node.name end;
  .roots | .. | select(.type? == "folder") | "\(.id)|\(path(.))"
' Bookmarks
```
Outputs pipe-delimited ID|path combinations through recursive path building[13][14].

### 2.3 Listing Folder Contents
**All children of folder ID 123:**
```bash
jq '.roots | .. | select(.id? == "123").children[]' Bookmarks
```

**Filter folders vs URLs:**
```bash
# Folders only
jq '.roots | .. | select(.id? == "123").children[] | select(.type == "folder")'

# URLs only
jq '.roots | .. | select(.id? == "123").children[] | select(.type == "url")'
```

### 2.4 Display Order Inspection
The `children` array order dictates UI presentation:
```bash
jq '.roots.bookmark_bar.children[].name' Bookmarks  # Lists items in toolbar order
```
Modify array indices to alter display sequence[13][14].

---

## III. Update Operations with `jq`

### 3.1 Adding New Bookmarks
```bash
new_bookmark=$(jq -n \
  --arg name "New Site" \
  --arg url "https://newsite.com" \
  '{type: "url", name: $name, url: $url, id: "9999"}')

jq --argjson new "$new_bookmark" \
  '.roots.bookmark_bar.children += [$new]' Bookmarks > tmp && mv tmp Bookmarks
```
Uses `--argjson` for structured data injection[10][12].

### 3.2 Modifying Existing Entries
**Update bookmark name:**
```bash
jq '(.roots | .. | select(.id? == "456")).name = "Updated Name"' Bookmarks > tmp && mv tmp Bookmarks
```

**Change parent folder:**
```bash
jq 'walk(
  if .id? == "456" then .parentId = "123" else . end
)' Bookmarks > tmp && mv tmp Bookmarks
```
Uses `walk` for deep traversal[13][14].

### 3.3 Reordering Items
Move item at index 2 to position 0:
```bash
jq '.roots.bookmark_bar.children = [.roots.bookmark_bar.children[2]] + .roots.bookmark_bar.children[:2] + .roots.bookmark_bar.children[3:]' Bookmarks > tmp && mv tmp Bookmarks
```

---

## IV. Advanced Scenarios

### 4.1 Batch Updates from CSV
```bash
# CSV format: old_id,new_name,new_url
while IFS=, read -r id name url; do
  jq --arg id "$id" --arg name "$name" --arg url "$url" \
    '(.roots | .. | select(.id? == $id)) |=
      .name = $name | .url = $url' Bookmarks > tmp && mv tmp Bookmarks
done  tmp && mv tmp Bookmarks
```

---

## V. Operational Considerations

### 5.1 Safety Measures
1. **Backup**: `cp Bookmarks Bookmarks.bak`
2. **Validation**: `jq empty Bookmarks` checks JSON integrity
3. **Atomic Writes**: Use `sponge` (from moreutils) for safe overwrites:
```bash
jq '...' Bookmarks | sponge Bookmarks
```

### 5.2 Browser Coordination
1. Close browser before editing
2. Checksum regeneration occurs on browser restart
3. Monitor `Last Modified` timestamp for changes

---

## VI. Performance Benchmarks

| Operation | 10k Bookmarks | Time (ms) |
|-----------|---------------|-----------|
| Read      | 2.1MB         | 120       |
| Add       | +1 entry      | 150       |
| Reorder   | 500 items     | 220       |

Tested on SSD with jq 1.7. Shows linear scaling with data size[13][14].

---

## VII. Alternative Approaches

### 7.1 Native Browser APIs
For active browser instances, prefer the `chrome.bookmarks` API:
```javascript
chrome.bookmarks.move("id123", {parentId: "id456"});
```

### 7.2 Hybrid Workflow
Combine `jq` preprocessing with API calls:
```bash
ids=$(jq -r '.roots | .. | select(.url? | contains("critical")).id' Bookmarks)
while read -r id; do
  chrome-cli bookmark-delete "$id"
done <<< "$ids"
```

---

## Conclusion
The `jq` utility provides a powerful mechanism for both querying and modifying Chromium bookmark data at scale. While browser APIs remain preferable for simple interactive changes, `jq` excels in batch operations and complex transformations. Key strengths include:

1. **Precision**: Surgical edits through JSONPath-like queries
2. **Reproducibility**: Scriptable changes for deployment
3. **Performance**: Handles large datasets efficiently

Future work could integrate real-time filesystem monitoring with `jq` pipelines for dynamic bookmark management. For mission-critical systems, combining `jq` preprocessing with formal API validation ensures both flexibility and data integrity.


# Programmatic Bookmark Manipulation in Running Chrome/Chromium Instances via DevTools Protocol

## Executive Summary
While Chromium browsers don't expose direct CLI access to bookmarks in running instances, the Chrome DevTools Protocol (CDP) enables remote control through WebSocket connections. This report details three methods for executing `chrome.bookmarks.move()`-equivalent operations on active browser sessions, including multi-profile environments.

---

## I. Protocol Fundamentals

### 1.1 Remote Debugging Requirements
Enable debugging per instance with unique ports:
```bash
# Start first profile
google-chrome --user-data-dir=/path/profile1 --remote-debugging-port=9222

# Second profile
google-chrome --user-data-dir=/path/profile2 --remote-debugging-port=9223
```

### 1.2 Authentication Flow
1. Retrieve WebSocket endpoints:
```bash
curl -s http://localhost:9222/json/list | jq '.[].webSocketDebuggerUrl'
```
2. Connect via WebSocket using obtained URL

---

## II. Execution Methods

### 2.1 Direct WebSocket Communication
```bash
# Install websocat
sudo apt install websocat

# Move bookmark ID 123 to parent 456
echo '{
  "id":1,
  "method":"Bookmarks.move",
  "params":{
    "id":"123",
    "destination":{
      "parentId":"456"
    }
  }
}' | websocat -n1 'ws://localhost:9222/devtools/page/ABC123'
```

### 2.2 Python Automation
```python
import websockets
import json

async def move_bookmark(ws_url, bookmark_id, new_parent):
    async with websockets.connect(ws_url) as websocket:
        payload = {
            "id": 1,
            "method": "Bookmarks.move",
            "params": {
                "id": bookmark_id,
                "destination": {"parentId": new_parent}
            }
        }
        await websocket.send(json.dumps(payload))
        print(await websocket.recv())

# Usage
import asyncio
asyncio.get_event_loop().run_until_complete(
    move_bookmark('ws://localhost:9222/devtools/page/ABC123', '123', '456')
)
```

### 2.3 Chrome-Remote Interface
```javascript
const CDP = require('chrome-remote-interface');

async function moveBookmark(port, bookmarkId, parentId) {
  const client = await CDP({port});
  const {Bookmarks} = client;

  try {
    await Bookmarks.move({
      id: bookmarkId,
      destination: {parentId}
    });
  } finally {
    await client.close();
  }
}

moveBookmark(9222, '123', '456');
```

---

## III. Multi-Instance Management

### 3.1 Profile/Port Mapping Table

| Data Directory | Port  | WebSocket Path          |
|----------------|-------|-------------------------|
| /path/profile1 | 9222  | /devtools/page/ABC123   |
| /path/profile2 | 9223  | /devtools/page/DEF456   |

### 3.2 Batch Operations
```bash
#!/bin/bash
declare -A PROFILE_PORTS=(
  ["/path/profile1"]=9222
  ["/path/profile2"]=9223
)

for profile in "${!PROFILE_PORTS[@]}"; do
  websocat "ws://localhost:${PROFILE_PORTS[$profile]}/devtools/browser"  {
  if (request.action === 'moveBookmark') {
    chrome.bookmarks.move(request.id, {parentId: request.parentId}, sendResponse);
    return true;
  }
});
```
Trigger via CLI:
```bash
curl -X POST http://localhost:9222/json/send \
  -H 'Content-Type: application/json' \
  -d '{"id":1,"method":"Runtime.evaluate","params":{"expression":"chrome.runtime.sendMessage(\"EXTENSION_ID\", {action:\"moveBookmark\", id:\"123\", parentId:\"456\"})"}}'
```

### 7.2 Native Messaging
Implement binary messenger:
```python
#!/usr/bin/env python3
import sys
import json
import struct

def read_message():
    raw_len = sys.stdin.buffer.read(4)
    msg_len = struct.unpack('@I', raw_len)[0]
    return json.loads(sys.stdin.buffer.read(msg_len).decode('utf-8'))

def send_message(msg):
    encoded = json.dumps(msg).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()

while True:
    msg = read_message()
    # Process bookmark move logic
    send_message({"success": True})
```

---

## VIII. Recommended Workflow

1. **Enable Debugging**: Start browsers with `--remote-debugging-port`
2. **Discover Targets**: Use `http://localhost:PORT/json/list` to find WebSocket URLs
3. **Execute Moves**: Choose method based on environment:
   - **CLI**: `websocat` for quick single operations
   - **Python**: Complex multi-step workflows
   - **Chrome-Remote**: Node.js environments
4. **Validate**: Check modified bookmarks via `chrome://bookmarks`

---

## Conclusion
While Chromium browsers don't natively expose bookmark manipulation via CLI in running instances, the Chrome DevTools Protocol provides robust programmatic control. For production systems, the Python CDP implementation offers the best balance of flexibility and error handling. Multi-profile operations require careful port management and target validation to ensure commands affect the correct browser instance.


"""
