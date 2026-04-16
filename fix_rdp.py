import re

content = open('rdp.html', 'r', encoding='utf-8').read()

# Replace Nav
content = content.replace('<title>環境データ管理 - 組織環境ナビゲーション</title>', '<title>RDP情報管理 - 組織環境ナビゲーション</title>')
content = content.replace('<h1>環境データ<span>管理</span></h1>', '<h1>RDP情報<span>管理</span></h1>')
content = content.replace('<a href="admin.html" class="active">データ管理</a>', '<a href="admin.html">データ管理</a>\n                <a href="rdp.html" class="active">RDP情報管理</a>')
content = content.replace('<p>既存の環境情報を修正、または新しい組織の情報を追加します</p>', '<p>リモートデスクトップ(RDP)の接続情報を管理します</p>')

# Replace grid
content = re.sub(r'grid-template-columns: .*?;', 'grid-template-columns: 2fr 1.5fr 1.5fr 3fr auto;', content)

# Replace data target
content = content.replace("fetch('data.csv?t='", "fetch('rdp.csv?t='")
content = content.replace('data.csv の読み', 'rdp.csv の読み')

# Replace Grid Editor Items
grid_html = """
                        <div>
                            <label>組織名</label>
                            <input type="text" value="${escapeHtml(item['組織名'])}" onchange="updateData(${idx}, '組織名', this.value)">
                        </div>
                        <div>
                            <label>RDPユーザー名</label>
                            <input type="text" value="${escapeHtml(item['RDPユーザー名'])}" onchange="updateData(${idx}, 'RDPユーザー名', this.value)">
                        </div>
                        <div>
                            <label>RDPパスワード</label>
                            <input type="text" value="${escapeHtml(item['RDPパスワード'])}" onchange="updateData(${idx}, 'RDPパスワード', this.value)">
                        </div>
                        <div>
                            <label>接続先(IP:Port)</label>
                            <input type="text" value="${escapeHtml(item['接続先(IP:Port)'] )}" onchange="updateData(${idx}, '接続先(IP:Port)', this.value)">
                        </div>
                        <div>
                            <button type="button" class="del-btn" onclick="deleteRow(${idx})" title="削除">削除</button>
                        </div>
"""
content = re.sub(r'<div>\s*<label>組織名</label>.*?(<div>\s*<button type="button" class="del-btn" onclick="deleteRow\(\$\{idx\}\)" title="削除">削除</button>\s*</div>)', grid_html, content, flags=re.DOTALL)

# Replace AddNewRow fields
content = re.sub(r"currentData\.unshift\(\{.*?\}\);", """currentData.unshift({
                '組織名': filterVal || '',
                'RDPユーザー名': '',
                'RDPパスワード': '',
                '接続先(IP:Port)': ''
            });""", content, flags=re.DOTALL)

# Replace filter check
content = re.sub(r"return \(row\['組織名'\] \|\| ''\)\.trim\(\) !== '' \|\| \(row\['構築環境名'\] \|\| ''\)\.trim\(\) !== '' \|\| \(row\['URL'\] \|\| ''\)\.trim\(\) !== '';", "return (row['組織名'] || '').trim() !== '';", content)

# Replace fields
content = content.replace('const fields = ["組織名", "構築環境名", "URL", "ログインID", "ログインパスワード", "DB名", "DBユーザー名", "DBパスワード"];', 'const fields = ["組織名", "RDPユーザー名", "RDPパスワード", "接続先(IP:Port)"];')

# Replace update jsp calling
content = content.replace("fetch('update_csv.jsp',", "fetch('update_rdp.jsp',")

with open('rdp.html', 'w', encoding='utf-8') as f:
    f.write(content)
