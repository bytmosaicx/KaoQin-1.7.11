from pathlib import Path
import re, sys

project = Path(sys.argv[1])
html = project / "app/src/main/assets/index.html"
gradle = project / "app/build.gradle"
s = html.read_text(encoding="utf-8")

backup = r"""async function cloudBackupNow(){let cfg;try{cfg=cloudGetConfig()}catch(e){alert(e.message);return}const defaultName=new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit'})+'考勤备份';let name=prompt('请为本次云备份命名：',defaultName);if(name===null)return;name=name.trim();if(!name||name.length>40){alert('备份名称不能为空且不能超过40个字符');return}if(!confirm('即将把本机考勤数据加密后上传云端。继续吗？'))return;try{const snapshot={format:'kaoqin-cloud-backup-v1',createdAt:new Date().toISOString(),appVersion:'1.7.59',storage:{}};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&!k.startsWith('jigong_cloud_'))snapshot.storage[k]=localStorage.getItem(k)}const encryptedData=await cloudEncrypt(snapshot,cfg.code);const res=await fetch(cfg.url+'/backup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code,encryptedData,name})});const out=await res.json();if(!res.ok||!out.ok)throw new Error(out.message||out.error||'云端备份失败');localStorage.setItem(CLOUD_TIME_KEY,String(Date.now()));cloudStatusRefresh();alert('云备份成功！\n备份名称：'+name+'\n云端最多保留最近5次备份。')}catch(e){alert('备份失败：'+(e.message||e))}}"""

restore = r"""async function cloudRestoreNow(){let cfg;try{cfg=cloudGetConfig()}catch(e){alert(e.message);return}const choice=prompt('请选择恢复方式：\n1、备份当前数据（推荐）\n2、直接覆盖恢复\n\n输入 1 或 2','1');if(choice===null)return;if(choice!=='1'&&choice!=='2'){alert('请输入 1 或 2');return}if(choice==='1'){let name=prompt('请为恢复前的本机备份命名：',new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit'})+'恢复前备份');if(name===null)return;name=name.trim();if(!name||name.length>40){alert('备份名称不能为空且不能超过40个字符');return}try{const snapshot={format:'kaoqin-cloud-backup-v1',createdAt:new Date().toISOString(),appVersion:'1.7.59',storage:{}};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&!k.startsWith('jigong_cloud_'))snapshot.storage[k]=localStorage.getItem(k)}const encryptedData=await cloudEncrypt(snapshot,cfg.code);const br=await fetch(cfg.url+'/backup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code,encryptedData,name})});const bo=await br.json();if(!br.ok||!bo.ok)throw new Error(bo.message||bo.error||'当前数据备份失败');localStorage.setItem(CLOUD_TIME_KEY,String(Date.now()));cloudStatusRefresh()}catch(e){alert('当前数据备份失败，已停止恢复：'+(e.message||e));return}}try{const lr=await fetch(cfg.url+'/backups',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code})});const lo=await lr.json();if(!lr.ok||!lo.ok||!Array.isArray(lo.backups))throw new Error(lo.message||lo.error||'云端服务尚不支持历史备份列表');const rows=lo.backups.slice(0,5);if(!rows.length)throw new Error('没有可恢复的云端备份');const labels=rows.map((r,i)=>(i+1)+'、'+(r.name||'未命名备份')+'（'+(r.createdAt?new Date(r.createdAt).toLocaleString('zh-CN',{hour12:false}):'时间未知')+'）').join('\n');const n=prompt('选择要恢复的备份序号：\n\n'+labels,'1');if(n===null)return;const ix=Number(n)-1;if(!Number.isInteger(ix)||ix<0||ix>=rows.length){alert('选择序号无效');return}const selected=rows[ix];const rr=await fetch(cfg.url+'/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code,id:selected.id})});const ro=await rr.json();if(!rr.ok||!ro.ok)throw new Error(ro.message||ro.error||'读取所选备份失败');const encrypted=ro.encryptedData||ro.data;if(typeof encrypted!=='string')throw new Error('云端返回的数据格式不正确');const snapshot=await cloudDecrypt(encrypted,cfg.code);if(!snapshot||snapshot.format!=='kaoqin-cloud-backup-v1'||!snapshot.storage)throw new Error('备份内容校验失败');pendingCloudRestoreSnapshot=snapshot;const rawTime=snapshot.createdAt||selected.createdAt;let backupTime='云端未提供备份时间';if(rawTime){const d=new Date(rawTime);if(!Number.isNaN(d.getTime()))backupTime=d.toLocaleString('zh-CN',{hour12:false})}$('cloudRestoreTime').textContent='备份名称：'+(selected.name||'未命名备份')+'\n备份时间：'+backupTime;$('cloudRestoreDialog').style.display='flex'}catch(e){alert('读取云端备份失败：'+(e.message||e))}}"""

def replace_function(source, name, replacement):
    pattern = re.compile(r"^async function " + re.escape(name) + r"\(\)\{.*$", re.M)
    source, count = pattern.subn(lambda _: replacement, source, count=1)
    if count != 1:
        raise SystemExit("未找到唯一函数：" + name)
    return source

s = replace_function(s, "cloudBackupNow", backup)
s = replace_function(s, "cloudRestoreNow", restore)
html.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, c = re.subn(r"versionCode\s+68", "versionCode 69", g, count=1)
g, n = re.subn(r"versionName\s+'1\.7\.58'", "versionName '1.7.59'", g, count=1)
if c != 1 or n != 1:
    raise SystemExit("版本号不是预期的 1.7.58，停止修改")
gradle.write_text(g, encoding="utf-8")
print("Applied 1.7.59 patch")
