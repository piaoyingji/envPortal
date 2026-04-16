const fs = require('fs');
let content = fs.readFileSync('rdp.html', 'utf-8');

content = content.replace('<title>環境データ管理 - 組織環境ナビゲーション</title>', '<title>RDP情報管理 - 組織環境ナビゲーション</title>');
content = content.replace('<h1>環境データ<span>管理</span></h1>', '<h1>RDP情報<span>管理</span></h1>');
// Fix Nav bar across all 3 files later via multi_replace, but here just do rdp.html
content = content.replace('<a href="admin.html" class="active">データ管理</a>', '<a href="admin.html">データ管理</a>\n                <a href="rdp.html" class="active">RDP情報管理</a>');
content = content.replace('<p>既存の環境情報を修正、または新しい組織の情報を追加します</p>', '<p>リモートデスクトップ(RDP)の接続情報を管理します</p>');

// Fix Grid Columns
content = content.replace(/grid-template-columns: .*?;/, 'grid-template-columns: 2fr 1.5fr 1.5fr 3fr auto;');
content = content.replace(/fetch\('data.csv\?t='/g, "fetch('rdp.csv?t='");
content = content.replace('data.csv の読み', 'rdp.csv の読み');

// Grid Items
const grid_html = `
                        <div>
                            <label>組織名</label>
                            <input type="text" value="\\${escapeHtml(item['組織名'])}" onchange="updateData(\\${idx}, '組織名', this.value)">
                        </div>
                        <div>
                            <label>RDPユーザー名</label>
                            <input type="text" value="\\${escapeHtml(item['RDPユーザー名'])}" onchange="updateData(\\${idx}, 'RDPユーザー名', this.value)">
                        </div>
                        <div>
                            <label>RDPパスワード</label>
                            <input type="text" value="\\${escapeHtml(item['RDPパスワード'])}" onchange="updateData(\\${idx}, 'RDPパスワード', this.value)">
                        </div>
                        <div>
                            <label>接続先(IP:Port)</label>
                            <input type="text" value="\\${escapeHtml(item['接続先(IP:Port)'] )}" onchange="updateData(\\${idx}, '接続先(IP:Port)', this.value)">
                        </div>
                        <div>
                            <button type="button" class="del-btn" onclick="deleteRow(\\${idx})" title="削除">削除</button>
                        </div>
`;
content = content.replace(/<div>\s*<label>組織名<\/label>.*?(<div>\s*<button type="button" class="del-btn" onclick="deleteRow\(\$\{idx\}\)" title="削除">削除<\/button>\s*<\/div>)/s, grid_html);

// AddNewRow
const addNewRowPattern = /currentData\.unshift\(\{[\s\S]*?\}\);/;
content = content.replace(addNewRowPattern, `currentData.unshift({
                '組織名': filterVal || '',
                'RDPユーザー名': '',
                'RDPパスワード': '',
                '接続先(IP:Port)': ''
            });`);

// Filter validation
content = content.replace(/return \(row\['組織名'\] \|\| ''\)\.trim\(\) !== ''.*?;/, "return (row['組織名'] || '').trim() !== '';");

// Fields
content = content.replace('const fields = ["組織名", "構築環境名", "URL", "ログインID", "ログインパスワード", "DB名", "DBユーザー名", "DBパスワード"];', 'const fields = ["組織名", "RDPユーザー名", "RDPパスワード", "接続先(IP:Port)"];');
content = content.replace(/update_csv\.jsp/g, 'update_rdp.jsp');

fs.writeFileSync('rdp.html', content);
