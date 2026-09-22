import { useEffect, useRef, useState } from "react";
import { ArrowUpLeft, Check, ShieldCheck } from "lucide-react";
import { GROK_PROVIDERS } from "@/lib/auth/providers";
import { signIn } from "@/lib/auth/client";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { useSelfStore } from "@/lib/store";
import * as THREE from "three";
import "@/styles/persian-bot-auth.css";
import "@/styles/persian-bot-premium.css";


function SpaceRealm() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const mount = ref.current; if (!mount) return;
    const scene = new THREE.Scene(); scene.background = new THREE.Color("#010307");
    const camera = new THREE.PerspectiveCamera(42, 1, .1, 500); camera.position.set(0,1,15);
    const renderer = new THREE.WebGLRenderer({antialias:true}); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setSize(mount.clientWidth,mount.clientHeight); renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping; mount.appendChild(renderer.domElement);
    scene.add(new THREE.AmbientLight("#9fb6c9",.45));
    const key=new THREE.DirectionalLight("#dcecf7",5); key.position.set(-5,8,10); scene.add(key);
    const rim=new THREE.PointLight("#9bc9eb",13,35,2); rim.position.set(5,3,4); scene.add(rim);
    const crownLight=new THREE.PointLight("#d2a95d",9,20,2); crownLight.position.set(0,5,4); scene.add(crownLight);
    const sg=new THREE.BufferGeometry(), count=1800, pos=new Float32Array(count*3);
    for(let i=0;i<count;i++){const r=55+Math.random()*130,a=Math.random()*Math.PI*2;pos[i*3]=Math.cos(a)*r;pos[i*3+1]=(Math.random()-.5)*100;pos[i*3+2]=Math.sin(a)*r-25;}
    sg.setAttribute("position",new THREE.BufferAttribute(pos,3)); scene.add(new THREE.Points(sg,new THREE.PointsMaterial({color:"#c9dbea",size:.085,transparent:true,opacity:.82})));
    const system=new THREE.Group(); scene.add(system);
    const sun=new THREE.Mesh(new THREE.SphereGeometry(1.6,32,32),new THREE.MeshStandardMaterial({color:"#c28f35",emissive:"#70450e",emissiveIntensity:2,roughness:.8})); sun.position.set(-8,5,-18); system.add(sun);
    [3.1,4.7,6.2].forEach((r,i)=>{const ring=new THREE.Mesh(new THREE.TorusGeometry(r,.007,8,180),new THREE.MeshBasicMaterial({color:"#91aabd",transparent:true,opacity:.14}));ring.rotation.x=Math.PI/2.2;ring.position.copy(sun.position);system.add(ring);const pl=new THREE.Mesh(new THREE.SphereGeometry([.15,.24,.35][i],18,18),new THREE.MeshStandardMaterial({color:["#71889a","#9c704e","#8c9ca0"][i],roughness:.9}));pl.position.set(sun.position.x+r,sun.position.y,sun.position.z);system.add(pl);});
    const panther=new THREE.Group(); panther.position.set(0,-2.5,0); scene.add(panther);
    const black=new THREE.MeshStandardMaterial({color:"#020304",roughness:.32,metalness:.5}), soft=new THREE.MeshStandardMaterial({color:"#080a0c",roughness:.55,metalness:.2}), ice=new THREE.MeshStandardMaterial({color:"#c4d7e4",metalness:.75,roughness:.2,emissive:"#1c2c38",emissiveIntensity:.25}), gold=new THREE.MeshStandardMaterial({color:"#c7a15a",metalness:.9,roughness:.18,emissive:"#3a250d",emissiveIntensity:.35});
    const add=(g:THREE.BufferGeometry,m:THREE.Material,p:[number,number,number],s=[1,1,1])=>{const x=new THREE.Mesh(g,m);x.position.set(...p);x.scale.set(...s);panther.add(x);return x;};
    add(new THREE.SphereGeometry(1.7,48,32),black,[0,2.45,0],[1.03,1.12,.88]);
    add(new THREE.SphereGeometry(1.2,36,24),soft,[0,1.25,.05],[.9,.78,.8]);
    add(new THREE.SphereGeometry(1.9,40,28),black,[0,-.25,-.1],[1.18,1.55,.8]);
    const ear=new THREE.ConeGeometry(.58,1.3,4); add(ear,black,[-1.05,3.75,0],[1,1,.72]).rotation.z=-.32; add(ear,black,[1.05,3.75,0],[1,1,.72]).rotation.z=.32;
    add(new THREE.SphereGeometry(.72,28,18),soft,[0,1.9,1],[1.2,.68,.72]);
    add(new THREE.SphereGeometry(.2,20,14),black,[0,1.78,1.62],[1.3,.8,.55]);
    const eye=new THREE.SphereGeometry(.13,20,12), eyeMat=new THREE.MeshStandardMaterial({color:"#e2f1fa",emissive:"#a9d8f5",emissiveIntensity:5,roughness:.08}); add(eye,eyeMat,[-.62,2.53,1.18],[1.5,.65,.5]); add(eye,eyeMat,[.62,2.53,1.18],[1.5,.65,.5]);
    const leg=new THREE.CapsuleGeometry(.36,1.75,8,16); [[-.72,-1.25,.1],[.72,-1.25,.1],[-.52,-1.45,-.25],[.52,-1.45,-.25]].forEach(p=>add(leg,black,p as [number,number,number]));
    const paw=new THREE.SphereGeometry(.48,24,16); [[-.75,-2.15,.42],[.75,-2.15,.42],[-.55,-2.3,.1],[.55,-2.3,.1]].forEach(p=>add(paw,soft,p as [number,number,number],[1.15,.55,1.35]));
    const curve=new THREE.CatmullRomCurve3([new THREE.Vector3(1,-.35,-.15),new THREE.Vector3(2.25,0,-.1),new THREE.Vector3(2.85,1,0),new THREE.Vector3(2.55,1.95,.1)]); panther.add(new THREE.Mesh(new THREE.TubeGeometry(curve,28,.2,12),black));
    const crown=new THREE.Group(); crown.position.y=4.15; panther.add(crown); crown.add(new THREE.Mesh(new THREE.CylinderGeometry(.95,1.15,.34,32),gold));
    for(let i=0;i<7;i++){const s=new THREE.Mesh(new THREE.ConeGeometry(.18,1.15,4),gold),a=i/7*Math.PI*2;s.position.set(Math.cos(a)*.8,.58,Math.sin(a)*.8);crown.add(s);}
    const gem=new THREE.Mesh(new THREE.OctahedronGeometry(.22,1),ice);gem.position.set(0,.45,1);crown.add(gem);
    const halo=new THREE.Mesh(new THREE.TorusGeometry(3.1,.055,10,120),new THREE.MeshBasicMaterial({color:"#9bb6c8",transparent:true,opacity:.23}));halo.position.set(0,.8,-1.4);halo.rotation.x=Math.PI/2.05;panther.add(halo);
    const base=new THREE.Mesh(new THREE.CylinderGeometry(3.4,4.2,.35,64),new THREE.MeshStandardMaterial({color:"#06090c",metalness:.75,roughness:.3}));base.position.y=-2.55;panther.add(base);
    const pointer={x:0,y:0}; const move=(e:PointerEvent)=>{const r=mount.getBoundingClientRect();pointer.x=(e.clientX-r.left)/r.width-.5;pointer.y=(e.clientY-r.top)/r.height-.5;}; mount.addEventListener("pointermove",move);
    const clock=new THREE.Clock(); let raf=0; const resize=()=>{camera.aspect=mount.clientWidth/Math.max(1,mount.clientHeight);camera.updateProjectionMatrix();renderer.setSize(mount.clientWidth,mount.clientHeight)}; const ro=new ResizeObserver(resize);ro.observe(mount);
    const loop=()=>{raf=requestAnimationFrame(loop);const t=clock.getElapsedTime();panther.rotation.y+=(pointer.x*.32-panther.rotation.y)*.018;panther.rotation.x+=(-pointer.y*.08-panther.rotation.x)*.018;panther.position.y=-2.5+Math.sin(t*.8)*.035;crown.rotation.y=Math.sin(t*.7)*.06;system.rotation.y=t*.025;renderer.render(scene,camera)};loop();
    return()=>{cancelAnimationFrame(raf);ro.disconnect();mount.removeEventListener("pointermove",move);renderer.dispose();mount.innerHTML=""};
  },[]);
  return <div className="pb-space3d" ref={ref} aria-hidden="true"/>;
}

export function Onboarding() {
  const { user, isPending } = useCurrentUserState();
  const complete = useSelfStore((s) => s.completeOnboarding);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  if (isPending) return <div className="pb-auth pb-auth--space" dir="rtl"><SpaceRealm /><div className="pb-auth__space-vignette" /><div className="pb-auth__loading"><div className="pb-auth__loading-card"><div className="pb-seal pb-seal--loading" aria-hidden><span>P</span><i /><b /></div><p className="pb-auth__loading-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · PRIVATE</p><h1 className="pb-auth__loading-title">در حال بررسی هویت</h1><div className="pb-auth__progress" aria-hidden><span /></div><p className="pb-auth__loading-copy">لطفاً چند لحظه صبر کنید…</p></div></div></div>;

  async function handleSignIn(providerId: string) {
    setBusy(providerId); setError("");
    try { await signIn(providerId, { callbackURL: "/" }); }
    catch (err) { setError(err instanceof Error ? err.message : "ورود انجام نشد. دوباره تلاش کنید."); setBusy(null); }
  }

  function enterWorkspace() {
    if (!user) return;
    complete(user.displayName || "کاربر سلف", user.primaryEmail?.split("@")[0] || "salf1_user", "Pᴇʀsɪᴀɴ ᴮᵒᵗ · SELF");
  }

  if (user) return (
    <div className="pb-auth" dir="rtl">
      <header className="pb-auth__top"><div className="pb-auth__brand"><div className="pb-auth__mini-seal" aria-hidden><span>P</span></div><div className="pb-auth__brand-copy"><strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong><small>پنل مدیریت سلف · PRIVATE</small></div></div><div className="pb-auth__secure"><i /><span>IDENTITY VERIFIED</span></div></header>
      <main className="pb-auth__verified"><section className="pb-auth__verified-visual"><div className="pb-seal pb-seal--verified" aria-hidden><span>P</span><i /><b /></div><p>IDENTITY VERIFIED</p></section><section className="pb-auth__card pb-auth__card--verified"><span className="pb-auth__eyebrow">AUTHENTICATION · COMPLETE</span><h1 className="pb-auth__card-title">هویت شما تأیید شد</h1><p className="pb-auth__card-desc">حساب شما با موفقیت شناسایی شد. اکنون می‌توانید وارد پنل مدیریت سلف شوید.</p><div className="pb-auth__identity"><div className="pb-auth__avatar">{user.displayName?.slice(0,1).toUpperCase() || "P"}</div><div className="pb-auth__identity-main"><strong>{user.displayName || "کاربر سلف"}</strong><span dir="ltr">{user.primaryEmail || "حساب تأییدشده"}</span></div><Check className="size-4" style={{color:"var(--pbx-green)"}} /></div><button type="button" onClick={enterWorkspace} className="pb-auth__enter">ورود به پنل مدیریت سلف<ArrowUpLeft className="size-4" /></button></section></main>
      <footer className="pb-auth__footer"><span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>پنل مدیریت سلف</span><span>Jawati · 2026</span></footer>
    </div>
  );

  return (
    <div className="pb-auth" dir="rtl">
      <header className="pb-auth__top"><div className="pb-auth__brand"><div className="pb-auth__mini-seal" aria-hidden><span>P</span></div><div className="pb-auth__brand-copy"><strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong><small>پنل مدیریت سلف · PRIVATE SELF MANAGEMENT</small></div></div><div className="pb-auth__secure"><i /><span>PRIVATE · SECURE</span></div></header>
      <main className="pb-auth__body pb-auth__body--space">
        <section className="pb-auth__intro pb-auth__intro--space"><div className="pb-auth__intro-line"><span>01</span><i /><span>IDENTITY GATE</span></div><div className="pb-auth__hero-seal"><div className="pb-seal" aria-hidden><span>P</span><i /><b /></div></div><p className="pb-auth__intro-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · PRIVATE ENVIRONMENT</p><h1 className="pb-auth__title">هویت،<br /><em>پیش از ورود.</em></h1><p className="pb-auth__lede">ورود به یک محیط خصوصی و دقیق؛ طراحی‌شده برای مدیریت سلف با تمرکز بر اصالت هویت، آرامش بصری و تجربه‌ای یکپارچه.</p><div className="pb-auth__signature">CRAFTED BY JAWATI · @JOWATI</div></section>
        <section className="pb-auth__card pb-auth__card--space"><div className="pb-auth__card-head"><span className="pb-auth__eyebrow">AUTHENTICATION</span><span className="pb-auth__status"><i /> READY</span></div><h2 className="pb-auth__card-title">هویت خود را تأیید کنید</h2><p className="pb-auth__card-desc">برای ورود به پنل مدیریت سلف، حساب خود را به‌صورت امن تأیید کنید.</p><div className="pb-auth__provider-list">{GROK_PROVIDERS.map((provider)=><button key={provider.providerId} type="button" className="pb-auth__provider" disabled={busy!==null} onClick={()=>handleSignIn(provider.providerId)}><span className="pb-auth__provider-mark">{provider.idp==="google"?"G":"X"}</span><span className="pb-auth__provider-copy"><strong>{busy===provider.providerId?"در حال اتصال…":"تأیید و ورود امن با "+provider.label}</strong><small>ارتباط رمزنگاری‌شده · انتقال امن به پنل</small></span><ArrowUpLeft className="pb-auth__provider-arrow size-4" /></button>)}</div>{error?<div className="pb-auth__error" role="alert">{error}</div>:null}<div className="pb-auth__divider"><span>PRIVATE ACCESS</span></div><div className="pb-auth__footnote"><ShieldCheck className="size-3.5" /><span>اطلاعات حساب شما فقط برای ایجاد یک ورود امن استفاده می‌شود.</span></div></section>
      </main>
      <footer className="pb-auth__footer"><span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>پنل مدیریت سلف</span><span>Jawati · 2026</span></footer>
    </div>
  );
}
