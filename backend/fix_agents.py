"""Patch agents.py: fix ServiceImpl example + key patterns."""
content = open('app/llm/agents.py', encoding='utf-8').read()

# Fix 1: Remove checkDuplicateWindowPk from example (teaches LLM to invent DAO methods)
old = (
    '                    "        for (WindowResDto dto : insertList) {\\n"\n'
    '                    "            if (syar030DaoImpl.checkDuplicateWindowPk(dto)) {\\n"\n'
    '                    "                throw new HscException(\\"CM0001\\");\\n"\n'
    '                    "            }\\n"\n'
    '                    "            syar030DaoImpl.insertWindow(dto);\\n"\n'
    '                    "        }\\n"\n'
    '                    "        syar030DaoImpl.updateWindow(updateList);\\n"\n'
    '                    "        syar030DaoImpl.deleteWindow(deleteList);\\n"\n'
)
new = (
    '                    "        for (WindowResDto dto : insertList) {\\n"\n'
    '                    "            syar030DaoImpl.insertWindow(dto);\\n"\n'
    '                    "        }\\n"\n'
    '                    "        if (!updateList.isEmpty()) syar030DaoImpl.updateWindow(updateList);\\n"\n'
    '                    "        if (!deleteList.isEmpty()) syar030DaoImpl.deleteWindow(deleteList);\\n"\n'
)
assert old in content, f"OLD string not found!"
content = content.replace(old, new, 1)
print("Fix 1: removed checkDuplicateWindowPk from example")

# Fix 2: Update key patterns to emphasize DAO whitelist
old2 = '                    "- save() takes List<ResDto> NOT single ReqDto\\n"\n'
new2 = ('                    "\u26a0\ufe0f save() takes List<ResDto> NOT single ReqDto \u2014 NEVER invent CpmsXxxSaveReqDto or new DTO\\n"\n')
if old2 in content:
    content = content.replace(old2, new2, 1)
    print("Fix 2: updated save() pattern warning")
else:
    print("Fix 2: pattern not found, checking...")
    idx = content.find("- save() takes List<ResDto>")
    print(f"  idx={idx}, context='{content[idx-5:idx+60]}'")

open('app/llm/agents.py', 'w', encoding='utf-8').write(content)
print("Done - agents.py updated")
