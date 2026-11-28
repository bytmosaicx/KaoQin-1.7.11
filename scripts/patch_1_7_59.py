from pathlib import Path
import re, sys

project = Path(sys.argv[1])
html = project / "app/src/main/assets/index.html"
gradle = project / "app/build.gradle"
s = html.read_text(encoding="utf-8")

helper = r"""
function cloudPickModal(title, message, buttons) {
  return new Promise(resolve => {
    const overlay=document.createElement('div');
    overlay.style.cssText='position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:22px;box-sizing:border-box';
    const panel=document.createElement('div');
    panel.style.cssText='width:100%;max-width:520px;background:#fff;border-radius:18px;padding:22px;box-sizing:border-box;color:#17211e;box-shadow:0 12px 40px rgba(0,0,0,.24);font-size:16px';
    const h=document.createElement('div');h.textContent=title;h.style.cssText='font-size:21px;font-weight:700;margin-bottom:12px';
    const p=document.createElement('div');p.textContent=message;p.style.cssText='white-space:pre-line;line-height:1.6;color:#53615b;margin-bottom:20px';
    const actions=document.createElement('div');actions.style.cssText='display:flex;flex-direction:column;gap:12px';
    function close(value){overlay.remove();resolve(value)}
    buttons.forEach(b=>{
      const el=document.createElement('button');el.type='button';el.textContent=b.text;
      el.style.cssText='width:100%;min-height:54px;border:0;border-radius:12px;padding:12px 16px;font-size:17px;font-weight:600;color:#fff;background:'+(b.color||'#16856d')+';text-align:center';
      el.addEventListener('click',()=>close(b.value));actions.appendChild(el);
    });
    panel.append(h,p,actions);overlay.appendChild(panel);document.body.appendChild(overlay);
  });
}
"""

backup = r"""async function cloudBackupNow(){let cfg;try{cfg=cloudGetConfig()}catch(e){alert(e.message);return}const defaultName=new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit'})+'考勤备份';let name=prompt('请为本次云备份命名：',defaultName);if(name===null)return;name=name.trim();if(!name||name.length>40){alert('备份名称不能为空且不能超过40个字符');return}if(!confirm('即将把本机考勤数据加密后上传云端。继续吗？'))return;try{const snapshot={format:'kaoqin-cloud-backup-v1',createdAt:new Date().toISOString(),appVersion:'1.7.60',storage:{}};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&!k.startsWith('jigong_cloud_'))snapshot.storage[k]=localStorage.getItem(k)}const encryptedData=await cloudEncrypt(snapshot,cfg.code);const res=await fetch(cfg.url+'/backup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code,encryptedData,name})});const out=await res.json();if(!res.ok||!out.ok)throw new Error(out.message||out.error||'云端备份失败');localStorage.setItem(CLOUD_TIME_KEY,String(Date.now()));cloudStatusRefresh();alert('云备份成功！\n备份名称：'+name)}catch(e){alert('备份失败：'+(e.message||e))}}"""

restore = r"""async function cloudRestoreNow(){let cfg;try{cfg=cloudGetConfig()}catch(e){alert(e.message);return}const choice=await cloudPickModal('选择恢复方式','请选择如何处理本机现有考勤数据。',[{text:'备份当前数据（推荐）',value:'backup',color:'#16856d'},{text:'直接覆盖恢复（不备份本机）',value:'overwrite',color:'#c7473d'},{text:'取消',value:'cancel',color:'#78827e'}]);if(choice==='cancel'||!choice)return;if(choice==='overwrite'&&!confirm('警告：直接覆盖后，本机当前考勤数据将被云端数据替换，且不会先备份本机数据。确定继续吗？'))return;if(choice==='backup'){let name=prompt('请为恢复前的本机备份命名：',new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit'})+'恢复前备份');if(name===null)return;name=name.trim();if(!name||name.length>40){alert('备份名称不能为空且不能超过40个字符');return}try{const snapshot={format:'kaoqin-cloud-backup-v1',createdAt:new Date().toISOString(),appVersion:'1.7.60',storage:{}};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&!k.startsWith('jigong_cloud_'))snapshot.storage[k]=localStorage.getItem(k)}const encryptedData=await cloudEncrypt(snapshot,cfg.code);const br=await fetch(cfg.url+'/backup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code,encryptedData,name})});const bo=await br.json();if(!br.ok||!bo.ok)throw new Error(bo.message||bo.error||'当前数据备份失败');localStorage.setItem(CLOUD_TIME_KEY,String(Date.now()));cloudStatusRefresh()}catch(e){alert('当前数据备份失败，已停止恢复：'+(e.message||e));return}}try{let rows=[],legacyData=null;const lr=await fetch(cfg.url+'/backups',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code})});let lo={};try{lo=await lr.json()}catch(e){}if(lr.ok&&lo.ok&&Array.isArray(lo.backups)){rows=lo.backups.slice(0,5)}else if(lr.status===404||String(lo.error||lo.message||'').includes('NOT_FOUND')){const rr=await fetch(cfg.url+'/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code})});let ro={};try{ro=await rr.json()}catch(e){}if(!rr.ok||!ro.ok)throw new Error(ro.message||ro.error||'旧版云端备份接口也无法读取，请检查云存档地址');legacyData=ro;rows=[{id:'__legacy__',name:'原有云端备份',createdAt:null}]}else{throw new Error(lo.message||lo.error||'云端历史备份读取失败')}if(!rows.length)throw new Error('没有可恢复的云端备份');const opts=rows.map((r,i)=>({text:(r.name||'未命名备份')+'  ·  '+(r.createdAt?new Date(r.createdAt).toLocaleString('zh-CN',{hour12:false}):'原有备份'),value:String(i),color:'#16856d'}));opts.push({text:'取消',value:'cancel',color:'#78827e'});const picked=await cloudPickModal('选择云端备份','点击一条记录即可选择恢复：',opts);if(picked==='cancel'||picked===null)return;const selected=rows[Number(picked)];let ro;if(selected.id==='__legacy__'){ro=legacyData}else{const rr=await fetch(cfg.url+'/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:cfg.code,id:selected.id})});ro=await rr.json();if(!rr.ok||!ro.ok)throw new Error(ro.message||ro.error||'读取所选备份失败')}const encrypted=ro.encryptedData||ro.data;if(typeof encrypted!=='string')throw new Error('云端返回的数据格式不正确');const snapshot=await cloudDecrypt(encrypted,cfg.code);if(!snapshot||snapshot.format!=='kaoqin-cloud-backup-v1'||!snapshot.storage)throw new Error('备份内容校验失败');pendingCloudRestoreSnapshot=snapshot;const rawTime=snapshot.createdAt||selected.createdAt;let backupTime='云端未提供备份时间';if(rawTime){const d=new Date(rawTime);if(!Number.isNaN(d.getTime()))backupTime=d.toLocaleString('zh-CN',{hour12:false})}$('cloudRestoreTime').textContent='备份名称：'+(selected.name||'原有云端备份')+'\n备份时间：'+backupTime;$('cloudRestoreDialog').style.display='flex'}catch(e){alert('读取云端备份失败：'+(e.message||e))}}"""

def replace_function(source, name, replacement):
    pattern = re.compile(r"^async function " + re.escape(name) + r"\(\)\{.*$", re.M)
    source, count = pattern.subn(lambda _: replacement, source, count=1)
    if count != 1:
        raise SystemExit("未找到唯一函数：" + name)
    return source

if "function cloudPickModal(" not in s:
    marker = "async function cloudBackupNow()"
    if marker not in s:
        raise SystemExit("未找到云备份入口")
    s = s.replace(marker, helper + "\n" + marker, 1)
s = replace_function(s, "cloudBackupNow", backup)
s = replace_function(s, "cloudRestoreNow", restore)
html.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
g, c = re.subn(r"versionCode\s+69", "versionCode 70", g, count=1)
g, n = re.subn(r"versionName\s+'1\.7\.59'", "versionName '1.7.60'", g, count=1)
if c != 1 or n != 1:
    raise SystemExit("版本号不是预期的 1.7.59，停止修改")
gradle.write_text(g, encoding="utf-8")
print("Applied 1.7.60 clickable restore and legacy fallback patch")
