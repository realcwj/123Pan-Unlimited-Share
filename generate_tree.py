import json
import os
import base64
from tqdm import tqdm

def get_icon(file_name):
    """
    根据文件名获取对应的图标。
    """
    file_type = file_name.split('.')[-1].lower()
    if file_type in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'svg','webp']:
        return "🖼️"
    elif file_type in ['mp3', 'wav', 'ogg', 'dsd', 'flac', 'aac', 'wma', 'm4a', 'mpc', 'ape', 'wv', 'wvx', 'dff', 'dsf', 'm4p']:
        return "🎵"
    elif file_type in ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm','3gp','m4v', 'ogv', 'asf', 'mts', 'm2ts', 'ts', 'mov']:
        return "🎥"
    elif file_type in ['zip', 'rar', '7z', 'tar', 'gz', 'bz2']:
        return "🗄️"
    else:
        return "📄"

def build_tree(data):
    """
    从文件列表中构建树形结构。
    """
    tree = {}
    # 首先，将所有项目按 ParentFileId 分组
    for item in data:
        parent_id = item.get("ParentFileId")
        if parent_id not in tree:
            tree[parent_id] = []
        tree[parent_id].append(item)

    # 为每个项目添加子项
    for item in data:
        item_id = item.get("FileId")
        if item_id in tree:
            item["children"] = sorted(tree[item_id], key=lambda x: x["FileName"]) # 按文件名排序子项
        else:
            item["children"] = []
    return tree

def generate_markdown_tree_recursive(nodes, indent_level=0, parent_id_map=None):
    """
    递归生成 Markdown 目录树。
    """
    markdown_lines = []
    indent = "  " * indent_level # 每个缩进级别使用两个空格

    # 对当前级别的节点按文件名排序
    # 我们需要确保只处理那些父ID存在于 parent_id_map 中的节点，
    # 或者对于顶层节点，它们的 ParentFileId 是我们预期的根父ID。
    # 在这个例子中，我们假设顶层节点的 ParentFileId 是那些在所有 FileId 中都不存在的ID，
    # 或者我们可以通过找到所有 ParentFileId 的集合，然后找到那些不在 FileId 中的 ParentFileId。
    # 一个更简单的方法是假设有一个共同的根 ParentFileId，或者从没有父ID的节点开始。

    # 在此实现中，我们将从 build_tree 返回的结构中，选择那些父ID为特定值的节点开始。
    # 或者，我们可以找到所有 ParentFileId，然后确定哪些是根节点。

    for node in nodes:
        prefix = "📁" if node.get("Type") == 1 else get_icon(node.get('FileName'))
        markdown_lines.append(f"{indent}- {prefix} {node['FileName']}")
        if node.get("Type") == 1 and node.get("children"):
            markdown_lines.extend(generate_markdown_tree_recursive(node["children"], indent_level + 1))
    return markdown_lines

def generate_markdown_from_json(json_data):
    """
    主函数，用于将 JSON 数据转换为 Markdown 目录树。
    """
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        return f"JSON 解析错误: {e}"

    if not data:
        return "JSON 数据为空。"

    # 构建文件ID到文件对象的映射，方便查找
    file_id_map = {item["FileId"]: item for item in data}

    # 构建父ID到子文件列表的映射
    parent_child_map = {}
    for item in data:
        parent_id = item.get("ParentFileId")
        if parent_id not in parent_child_map:
            parent_child_map[parent_id] = []
        parent_child_map[parent_id].append(item)

    # 找出根节点 (ParentFileId 不在任何 FileId 中的节点，或者具有特定已知根ID的节点)
    all_file_ids = set(file_id_map.keys())
    root_nodes = []

    # 确定哪些是顶层文件夹/文件
    # 顶层元素的 ParentFileId 可能是一个特定的值，或者是不存在于任何 FileId 中的值
    # 为了通用性，我们假设顶层元素的 ParentFileId 是那些在所有 FileId 中都不存在的 ParentFileId
    # 或者，如果所有元素都有一个共同的 ParentFileId，那么这就是根。
    
    # 查找所有父ID
    parent_ids_set = set(item.get("ParentFileId") for item in data if item.get("ParentFileId") is not None)
    
    # 找到那些作为父ID但不是任何项目的FileID的ID，这些就是根目录的父ID
    # 或者，如果结构中有一个明确的“根”文件夹，其ParentFileId为None或特定值
    
    # 简单的处理方式：找到ParentFileId出现频率最高且不为任何FileId的ID
    # 或者，通常顶层文件/文件夹会有一个共同的 ParentFileId。
    # 在给定的例子中，所有列出的项目都有 ParentFileId: 19909413。
    # 我们需要找到这个 "19909413" 本身的信息（如果它也是一个条目的话），
    # 或者假设它是虚拟的根。

    # 假设我们从具有最小 ParentFileId 且该 ParentFileId 不作为任何 FileId 的节点开始，
    # 或者，更简单地，如果所有项目都有一个共同的 ParentFileId，我们可以从那里开始。

    # 修正查找根节点的方法：
    # 根节点是那些 ParentFileId 不在所有 FileId 集合中的节点，
    # 或者 ParentFileId 为 None/null/特定根 sentinel 值的节点。
    # 在示例数据中，所有项的 ParentFileId 都是 19909413。
    # 我们需要找到这个 19909413 对应的对象（如果存在），或者假设它是树的起点。

    # 如果 ParentFileId 为 X 的所有子节点构成一个层级，
    # 那么我们需要找到那个“根” ParentFileId。

    # 让我们假设根节点的 ParentFileId 是那些不存在于任何 FileId 中的 ParentFileId
    root_parent_ids = [pid for pid in parent_ids_set if pid not in all_file_ids]

    if not root_parent_ids and parent_ids_set:
        # 如果所有 ParentFileId 同时也都是 FileId，这可能意味着是一个循环引用或者
        # 数据代表了一个更大的文件系统的一部分。
        # 在这种情况下，我们可以选择 ParentFileId 最小的那个作为起点，
        # 或者，如示例所示，所有项共享一个 ParentFileId。
        # 我们假设以共享的 ParentFileId 下的节点作为第一级。
        # 在示例中，所有项目都有 ParentFileId: 19909413。
        # 如果这个 19909413 也在 FileId 中，它就是一个文件夹。
        # 否则，它是一个虚拟的根。

        # 我们从所有 ParentFileId 中找到最顶层的 ParentFileId。
        # 一个常见的场景是，会有一个或多个 ParentFileId 作为所有其他项的起点。
        # 例如，所有示例项的 ParentFileId 都是 19909413。
        # 我们可以将这个ID视为根目录的ID。
        
        # 找到所有项目的共同 ParentFileId (如果存在)
        # 或者找到那些 ParentFileId 不在 file_id_map 中的条目
        
        processed_root_parents = set()
        for item in data:
            parent_id = item.get("ParentFileId")
            if parent_id not in all_file_ids and parent_id not in processed_root_parents:
                if parent_id in parent_child_map: # 确保这个父ID下确实有子节点
                    # 对父ID下的子节点进行排序
                    children = sorted(parent_child_map[parent_id], key=lambda x: (x.get("Type", 0), x["FileName"])) # 文件夹优先，然后按名称
                    root_nodes.extend(children)
                    processed_root_parents.add(parent_id)
            elif parent_id is None and parent_id not in processed_root_parents: # 处理 ParentFileId 为 null 的情况
                 if parent_id in parent_child_map:
                    children = sorted(parent_child_map[parent_id], key=lambda x: (x.get("Type", 0), x["FileName"]))
                    root_nodes.extend(children)
                    processed_root_parents.add(parent_id)

        # 如果经过上述处理后 root_nodes 仍为空，并且 parent_child_map 不为空
        # 这可能意味着所有的 ParentFileId 都是有效的 FileId
        # 这种情况下，我们需要找到一个或多个“顶级”文件夹/文件
        # 例如，在示例中，所有 ParentFileId 都是 19909413。
        # 如果 19909413 也在 FileId 中，则它是一个文件夹，其子项是第一级。
        # 如果 19909413 不是 FileId，则其子项是第一级。

        if not root_nodes and parent_child_map:
            # 尝试找到一个共同的父ID，作为起点
            # 在本例中，这个共同的父ID是 19909413
            # 我们需要找到这个父ID对应的子节点
            # 为了简单起见，我们先构建完整的子节点映射
            for item_id in file_id_map:
                if item_id in parent_child_map:
                    # 按类型（文件夹优先）然后按名称排序子项
                    file_id_map[item_id]["children"] = sorted(parent_child_map[item_id], key=lambda x: (x.get("Type", 0), x["FileName"]))
                else:
                    file_id_map[item_id]["children"] = []
            
            # 现在确定根节点：那些 ParentFileId 不在 FileId 集合中的项，或者是具有特定根 ParentFileId 的项。
            # 在示例数据中，ParentFileId 19909413 是所有列出项的父级。
            # 我们需要找到 FileId 为 19909413 的那个项目（如果存在），或者直接处理它的子项目。
            # 假设 19909413 是一个文件夹的 ID，而这个文件夹条目本身可能不在我们当前处理的列表中，
            # 或者它在列表中但没有 ParentFileId (或 ParentFileId 指向更上层)。

            # 基于示例，所有条目的 ParentFileId 都是 19909413。
            # 我们应该将 FileId 为 19909413 的条目（如果存在）作为根，或者将这些条目作为根下的第一级。
            # 由于示例中没有 FileId 为 19909413 的条目，我们假设这些条目是第一级。
            
            # 重新思考根节点的确定：
            # 1. 找到所有 ParentFileId。
            # 2. 找到所有 FileId。
            # 3. 根节点的 ParentFileId 是那些不在 FileId 集合中的 ParentFileId。
            
            current_parent_ids = set(item['ParentFileId'] for item in data if 'ParentFileId' in item)
            current_file_ids = set(item['FileId'] for item in data)
            
            # 找出作为父ID但本身不是文件ID的ID，这些是“根”的父ID
            root_level_parent_ids = current_parent_ids - current_file_ids
            
            if not root_level_parent_ids and current_parent_ids: # 如果所有父ID也都是文件ID
                # 这意味着我们可能只得到了一个子树。
                # 在这种情况下，我们可以选择所有 ParentFileId 中最小的那个作为“根”的父ID，
                # 或者，如果只有一个 ParentFileId，就用它。
                if len(current_parent_ids) == 1:
                    root_level_parent_ids = current_parent_ids
                else: # 复杂情况，选择最小的parent_id作为开始
                    if current_parent_ids:
                         root_level_parent_ids = {min(pid for pid in current_parent_ids if pid is not None)}

            for root_pid in sorted(list(root_level_parent_ids)): # 排序以保证根顺序确定性
                if root_pid in parent_child_map:
                     # 对根节点下的第一级进行排序
                    children_of_root_pid = sorted(parent_child_map[root_pid], key=lambda x: (x.get("Type", 0), x["FileName"]))
                    root_nodes.extend(children_of_root_pid)
            
            # 如果 root_nodes 仍然为空，但数据不为空，则所有节点可能都是根节点（没有ParentFileId）
            if not root_nodes and data:
                root_nodes = [item for item in data if item.get("ParentFileId") is None]
                if not root_nodes: # 如果所有节点都有ParentFileId，但我们没找到根
                                   # 这意味着数据可能不完整或结构特殊。
                                   # 对于给定的示例，所有ParentFileId都是一样的，并且该ID本身不在FileId中。
                                   # 所以，parent_child_map[19909413] 应该是第一级。
                    first_parent_id = data[0].get("ParentFileId") # 假设所有项来自同一个父级，如示例所示
                    if first_parent_id is not None and first_parent_id in parent_child_map:
                        root_nodes = sorted(parent_child_map[first_parent_id], key=lambda x: (x.get("Type", 0), x["FileName"]))

    if not root_nodes:
        # 如果找不到明确的根节点，但有数据，则将所有数据视为根级别（不推荐，除非数据确实是扁平的）
        # 或者，更可能的情况是，我们需要一个顶层文件夹的名称。
        # 对于给定的示例，所有项目的 ParentFileId 都是 19909413。
        # 我们应该获取所有以 19909413 为父项的子项。
        
        # 再次简化根节点查找逻辑，专门针对示例结构
        # 构建完整的树结构，包含子节点信息
        items_by_id = {item['FileId']: item for item in data}
        for item in data:
            item['children'] = [] # 初始化子节点列表
        
        roots_final = []
        parent_to_children_map_final = {}

        for item in data:
            parent_id = item.get('ParentFileId')
            if parent_id not in parent_to_children_map_final:
                parent_to_children_map_final[parent_id] = []
            parent_to_children_map_final[parent_id].append(item)

        # 现在为每个节点（如果它在items_by_id中）填充其子节点
        for item_id, item_data in items_by_id.items():
            if item_id in parent_to_children_map_final: # 如果这个item是某些其他item的父级
                 # 按类型（文件夹优先）然后按名称排序子项
                item_data['children'] = sorted(parent_to_children_map_final[item_id], key=lambda x: (x.get("Type", 0), x["FileName"]))

        # 确定实际的根节点：其 ParentFileId 不在 FileId 集合中的那些节点
        all_file_ids_final = set(items_by_id.keys())
        
        # 遍历 parent_to_children_map_final，找到那些父ID不是任何文件ID的条目
        # 这些父ID下的子节点就是我们的顶层节点
        root_level_items = []
        root_parent_candidates = set(parent_to_children_map_final.keys())
        
        actual_root_parents = root_parent_candidates - all_file_ids_final
        
        if not actual_root_parents and root_parent_candidates: # 如果所有父ID也是文件ID
            # 这意味着我们可能需要找到一个或多个没有父ID的节点，或者特定ID的节点
            # 对于示例，19909413 是父ID，但不是文件ID
            pass # actual_root_parents 应该已经包含了 19909413

        for pid in sorted(list(actual_root_parents)): # 排序以保证一致性
            if pid in parent_to_children_map_final:
                 # 按类型（文件夹优先）然后按名称排序子项
                root_level_items.extend(sorted(parent_to_children_map_final[pid], key=lambda x: (x.get("Type", 0), x["FileName"])))
        
        if not root_level_items and data: # 如果还没有找到根，并且有数据
            # 检查是否有 ParentFileId 为 None 的项
            none_parent_items = [item for item in data if item.get("ParentFileId") is None]
            if none_parent_items:
                 # 按类型（文件夹优先）然后按名称排序子项
                root_level_items = sorted(none_parent_items, key=lambda x: (x.get("Type", 0), x["FileName"]))
            else:
                # 如果所有项都有 ParentFileId，并且这些 ParentFileId 都在 FileId 中，
                # 那么我们需要找到“最顶层”的那些节点（即其父节点本身不是其他节点的子节点）
                # 这种情况比较复杂，通常数据会有一个明确的入口点。
                # 对于给定的例子，19909413是所有条目的父级，但它本身不在列表中。
                # 因此，parent_to_children_map_final[19909413] 将是根节点。
                # 之前 actual_root_parents 的逻辑应该能处理这个。
                # 如果你的 JSON 总是像示例一样，有一个共同的 ParentFileId，并且这个 ParentFileId 不在 FileId 中，
                # 那么上面的 actual_root_parents 逻辑是正确的。
                pass

        if not root_level_items and data:
             # Fallback: if no clear roots are found, assume all items without a ParentFileId present in FileId map are roots.
             # Or, if all items share a common ParentFileId not in FileId map, those items are roots.
             # For the given example, all items share ParentFileId 19909413, which is not a FileId in the list.
             # So, parent_to_children_map_final[19909413] contains the root items.
             # This was handled by the 'actual_root_parents' logic.
             # If still no roots, it could be that the input is just one level of a deeper tree, and we should display it.
             # Or data is malformed.
             # Last resort: if only one parent_id is present across all items, use children of that.
            parent_ids_in_data = list(set(item.get("ParentFileId") for item in data))
            if len(parent_ids_in_data) == 1 and parent_ids_in_data[0] is not None:
                common_parent_id = parent_ids_in_data[0]
                if common_parent_id in parent_to_children_map_final:
                    root_level_items = sorted(parent_to_children_map_final[common_parent_id], key=lambda x: (x.get("Type", 0), x["FileName"]))

        markdown_lines = generate_markdown_tree_recursive(root_level_items)
        return "\n".join(markdown_lines)

    # -------------------------------------------------------------------------
    # 更健壮和清晰的树构建方法
    # -------------------------------------------------------------------------
    items_map = {item['FileId']: item for item in data} # 方便通过ID查找项目
    for item_id in items_map:
        items_map[item_id]['children'] = [] # 初始化子节点列表

    root_items_for_md = [] # 存储顶级项目以供 Markdown 生成

    for item_id, item_data in items_map.items():
        parent_id = item_data.get('ParentFileId')
        if parent_id is not None and parent_id in items_map:
            # 如果父ID存在于我们的项目列表中，则将此项目添加为父项目的子项目
            items_map[parent_id]['children'].append(item_data)
        else:
            # 如果父ID不存在于项目列表中 (例如 ParentFileId 指向列表之外的ID，或者为 None)
            # 则此项目是一个根项目或其父项目不在当前数据集中
            root_items_for_md.append(item_data)

    # 对每个节点的子节点进行排序
    for item_id in items_map:
        # 文件夹优先 (Type=1)，然后按文件名排序
        items_map[item_id]['children'].sort(key=lambda x: (not x.get("Type") == 1, x['FileName']))
    
    # 对顶级项目进行排序
    # 文件夹优先 (Type=1)，然后按文件名排序
    root_items_for_md.sort(key=lambda x: (not x.get("Type") == 1, x['FileName']))

    # 如果根节点列表为空，但数据不为空，这可能意味着所有项都有一个共同的父ID，
    # 而这个父ID本身不在数据项中（就像示例中一样）。
    if not root_items_for_md and data:
        # 找出所有父ID
        all_parent_ids = set(item.get("ParentFileId") for item in data if item.get("ParentFileId") is not None)
        all_actual_file_ids = set(item["FileId"] for item in data)
        
        # 外部父ID是那些作为父ID出现但不是任何文件/文件夹的ID的ID
        external_parent_ids = all_parent_ids - all_actual_file_ids
        
        if external_parent_ids:
            # 从这些外部父ID开始构建树
            temp_roots = []
            for ext_pid in sorted(list(external_parent_ids)): # 排序以保证顺序
                for item_data_val in data: # 遍历原始数据查找子项
                    if item_data_val.get("ParentFileId") == ext_pid:
                        # 我们需要确保子项的子项也正确链接
                        # 最好的方法是使用 items_map 中的项，因为它们已经处理了 'children'
                        temp_roots.append(items_map[item_data_val['FileId']])
            
            # 对这些找到的根节点进行排序
            temp_roots.sort(key=lambda x: (not x.get("Type") == 1, x['FileName']))
            root_items_for_md = temp_roots
        elif not data[0].get("ParentFileId"): # 处理没有ParentFileId的根节点情况
             root_items_for_md = [items_map[item['FileId']] for item in data if not item.get("ParentFileId")]
             root_items_for_md.sort(key=lambda x: (not x.get("Type") == 1, x['FileName']))

    if not root_items_for_md and data:
        # 如果仍然没有根，并且有数据，这表示可能是一个孤立的子树，
        # 或者所有项目都有父级，但父级也在列表中。
        # 这是一个复杂的情况，取决于期望的行为。
        # 对于给定的示例，上面的 external_parent_ids 逻辑应该可以工作。
        # 如果仍然没有，则表示所有 ParentFileId 都在 FileId 中。
        # 这种情况下，我们需要找到那些不被任何其他项作为子项引用的项的父项。
        # 或者更简单：如果所有项目都有相同的 ParentFileId，并且这个 ParentFileId 也在 FileId 列表中。
        # 比如：
        # [ {FileId:1, FileName:"RootFolder", Type:1, ParentFileId:null},
        #   {FileId:2, FileName:"Sub1", Type:1, ParentFileId:1},
        #   {FileId:3, FileName:"File1.txt", Type:0, ParentFileId:2} ]
        # 此时 root_items_for_md 会包含 FileId:1 的项目。

        # 如果示例JSON是：
        # [ {FileId:10, FileName:"FolderA", Type:1, ParentFileId:1}, <- 1 不在列表中
        #   {FileId:11, FileName:"FolderB", Type:1, ParentFileId:1} ]
        # external_parent_ids 会是 {1}，然后 temp_roots 会包含 FolderA 和 FolderB。

        # 如果示例JSON是（所有项目都有父级，且父级在列表中，但没有一个ParentFileId为null/外部）：
        # [ {FileId:1, FileName:"F1", ParentFileId:3, Type:1},
        #   {FileId:2, FileName:"F2", ParentFileId:1, Type:1},
        #   {FileId:3, FileName:"F3", ParentFileId:2, Type:1} ] <- 循环或不完整的树
        # 这种情况下，上述逻辑可能无法确定明确的根。
        # 一个策略是选择FileId最小且没有被其他项作为子项引用的项的父项下的子项。
        # 但这超出了基本树构建的范围。对于所给的JSON，external_parent_ids方法是合适的。
        return "无法确定目录树的根节点。请检查数据结构。"

    markdown_lines = []
    def build_md_lines_recursive(nodes, indent_level):
        indent = "  " * indent_level
        for node in nodes: # nodes 已经排序
            prefix = "📁" if node.get("Type") == 1 else get_icon(node.get('FileName'))
            markdown_lines.append(f"{indent}- {prefix} {node['FileName']}")
            if node.get("Type") == 1 and node.get("children"):
                build_md_lines_recursive(node["children"], indent_level + 1)

    build_md_lines_recursive(root_items_for_md, 0)
    return "\n".join(markdown_lines)

# 批量读取文件夹内的 *.123share 文件数据

FULL_TEXT = ""

SHARE_PATH = os.path.abspath("./share")
SHARE_FILES = [_ for _ in os.listdir(SHARE_PATH) if _.endswith(".123share")]
for SINGLE_FILE in tqdm(SHARE_FILES):
    CURRENT_DATAS = []
    with open(os.path.join(SHARE_PATH, SINGLE_FILE), "rb") as f:
        _temp_datas = json.loads(base64.b64decode(f.read()).decode("utf-8"))
    for each in _temp_datas:
        CURRENT_DATAS.append({
            "FileId": each["FileId"],
            "FileName": each["FileName"],
            "ParentFileId": each["parentFileId"],
            "Type": each["Type"],
        })
    tree_output = generate_markdown_from_json(json.dumps(CURRENT_DATAS))
    FULL_TEXT += f"☁️ 文件：{SINGLE_FILE}\n"
    for line in tree_output.split("\n"):
        FULL_TEXT += f"  {line}\n"

with open("./TREE.md", "w", encoding="utf-8") as f:
    f.write(FULL_TEXT)
