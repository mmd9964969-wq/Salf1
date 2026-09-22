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
    const mount = ref.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#010408");
    scene.fog = new THREE.FogExp2("#02070b", 0.012);

    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 420);
    camera.position.set(0, 1.15, 17);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    mount.appendChild(renderer.domElement);

    const ambient = new THREE.HemisphereLight("#b8cedd", "#020304", 1.15);
    scene.add(ambient);

    const key = new THREE.DirectionalLight("#dbeaf5", 3.4);
    key.position.set(-6, 8, 9);
    scene.add(key);

    const coldRim = new THREE.PointLight("#9dd8ff", 18, 38, 2);
    coldRim.position.set(5, 3.8, 4.5);
    scene.add(coldRim);

    const edgeRim = new THREE.PointLight("#557b98", 12, 32, 2);
    edgeRim.position.set(-7, 1.5, -1);
    scene.add(edgeRim);

    const crownLight = new THREE.PointLight("#d9b36c", 11, 22, 2);
    crownLight.position.set(0, 6.2, 3);
    scene.add(crownLight);

    const starCount = window.innerWidth < 900 ? 900 : 1900;
    const starGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    const starSizes = new Float32Array(starCount);

    for (let i = 0; i < starCount; i++) {
      const radius = 48 + Math.random() * 160;
      const theta = Math.random() * Math.PI * 2;
      const y = (Math.random() - 0.5) * 110;
      starPositions[i * 3] = Math.cos(theta) * radius;
      starPositions[i * 3 + 1] = y;
      starPositions[i * 3 + 2] = Math.sin(theta) * radius - 45;
      starSizes[i] = 0.45 + Math.random() * 1.8;
    }

    starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
    starGeometry.setAttribute("aSize", new THREE.BufferAttribute(starSizes, 1));

    const starMaterial = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms: { uPixelRatio: { value: renderer.getPixelRatio() } },
      vertexShader: `
        attribute float aSize;
        uniform float uPixelRatio;
        void main() {
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = aSize * uPixelRatio * (34.0 / max(1.0, -mvPosition.z));
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        void main() {
          vec2 uv = gl_PointCoord - 0.5;
          float d = length(uv);
          float alpha = smoothstep(0.5, 0.02, d);
          gl_FragColor = vec4(0.74, 0.84, 0.92, alpha * 0.78);
        }
      `,
    });

    scene.add(new THREE.Points(starGeometry, starMaterial));

    const solarSystem = new THREE.Group();
    scene.add(solarSystem);

    const sunMaterial = new THREE.MeshStandardMaterial({
      color: "#c99547",
      emissive: "#7a4d14",
      emissiveIntensity: 2.8,
      roughness: 0.7,
      metalness: 0.05,
    });
    const sun = new THREE.Mesh(new THREE.SphereGeometry(1.7, 40, 40), sunMaterial);
    sun.position.set(-8.8, 5.8, -22);
    solarSystem.add(sun);

    const orbitalRadii = [3.8, 5.6, 7.3];
    orbitalRadii.forEach((radius, index) => {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(radius, 0.012, 8, 220),
        new THREE.MeshBasicMaterial({
          color: "#9fb8c9",
          transparent: true,
          opacity: 0.12 - index * 0.02,
        }),
      );
      ring.position.copy(sun.position);
      ring.rotation.set(Math.PI / 2.2, 0, 0);
      solarSystem.add(ring);

      const planet = new THREE.Mesh(
        new THREE.SphereGeometry([0.18, 0.27, 0.38][index], 26, 20),
        new THREE.MeshStandardMaterial({
          color: ["#718b9f", "#946b4e", "#87969c"][index],
          roughness: 0.92,
          metalness: 0.08,
        }),
      );
      planet.position.set(sun.position.x + radius, sun.position.y, sun.position.z);
      solarSystem.add(planet);
    });

    const panther = new THREE.Group();
    panther.position.set(0, -2.9, 0.2);
    scene.add(panther);

    const fur = new THREE.MeshPhysicalMaterial({
      color: "#050709",
      roughness: 0.48,
      metalness: 0.16,
      clearcoat: 0.22,
      clearcoatRoughness: 0.42,
    });
    const furDark = new THREE.MeshPhysicalMaterial({
      color: "#020304",
      roughness: 0.58,
      metalness: 0.1,
      clearcoat: 0.12,
      clearcoatRoughness: 0.5,
    });
    const muzzleMat = new THREE.MeshPhysicalMaterial({
      color: "#0a0d10",
      roughness: 0.62,
      metalness: 0.05,
      clearcoat: 0.16,
    });
    const noseMat = new THREE.MeshPhysicalMaterial({
      color: "#0b0c0d",
      roughness: 0.32,
      metalness: 0.15,
      clearcoat: 0.42,
    });
    const eyeMat = new THREE.MeshPhysicalMaterial({
      color: "#eaf7ff",
      emissive: "#8edbff",
      emissiveIntensity: 5.2,
      roughness: 0.08,
      metalness: 0.2,
      clearcoat: 0.7,
    });
    const crownMat = new THREE.MeshPhysicalMaterial({
      color: "#10151a",
      metalness: 0.96,
      roughness: 0.17,
      clearcoat: 0.8,
      clearcoatRoughness: 0.12,
      emissive: "#1b2934",
      emissiveIntensity: 0.22,
    });
    const gemMat = new THREE.MeshPhysicalMaterial({
      color: "#d7f1ff",
      emissive: "#71c7f6",
      emissiveIntensity: 1.7,
      metalness: 0.65,
      roughness: 0.08,
      transmission: 0.25,
      thickness: 0.6,
    });

    const add = (
      geometry: THREE.BufferGeometry,
      material: THREE.Material,
      position: [number, number, number],
      scale: [number, number, number] = [1, 1, 1],
    ) => {
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(...position);
      mesh.scale.set(...scale);
      panther.add(mesh);
      return mesh;
    };

    // Torso, shoulders, hips and neck: layered silhouette for a more natural feline anatomy.
    add(new THREE.SphereGeometry(1.75, 64, 44), fur, [0, -0.15, -0.18], [1.18, 1.52, 0.9]);
    add(new THREE.SphereGeometry(1.05, 48, 32), fur, [-0.78, 0.28, 0.05], [0.9, 1.08, 0.92]);
    add(new THREE.SphereGeometry(1.05, 48, 32), fur, [0.78, 0.28, 0.05], [0.9, 1.08, 0.92]);
    add(new THREE.SphereGeometry(0.9, 44, 30), furDark, [0, 1.16, 0.02], [0.94, 1.15, 0.94]);

    // Head / cheeks / muzzle.
    add(new THREE.SphereGeometry(1.48, 64, 44), fur, [0, 2.65, 0.03], [1.02, 1.08, 0.96]);
    add(new THREE.SphereGeometry(0.92, 48, 32), furDark, [-0.72, 2.28, 0.14], [0.92, 0.76, 0.86]);
    add(new THREE.SphereGeometry(0.92, 48, 32), furDark, [0.72, 2.28, 0.14], [0.92, 0.76, 0.86]);
    add(new THREE.SphereGeometry(0.8, 44, 30), muzzleMat, [0, 2.16, 0.97], [1.06, 0.64, 0.72]);
    add(new THREE.SphereGeometry(0.34, 32, 24), noseMat, [0, 2.1, 1.54], [1.14, 0.68, 0.72]);
    add(new THREE.SphereGeometry(0.52, 32, 24), furDark, [0, 1.86, 1.08], [0.76, 0.42, 0.52]);

    // Ears with inner cool-black surfaces.
    const earGeometry = new THREE.ConeGeometry(0.7, 1.65, 4);
    const leftEar = add(earGeometry, fur, [-0.98, 3.78, 0.02], [0.9, 1.08, 0.72]);
    leftEar.rotation.z = -0.2;
    leftEar.rotation.x = 0.08;
    const rightEar = add(earGeometry, fur, [0.98, 3.78, 0.02], [0.9, 1.08, 0.72]);
    rightEar.rotation.z = 0.2;
    rightEar.rotation.x = 0.08;

    const innerEarMat = new THREE.MeshStandardMaterial({
      color: "#10161c",
      roughness: 0.95,
      metalness: 0.04,
    });
    add(new THREE.ConeGeometry(0.38, 1.0, 4), innerEarMat, [-0.98, 3.77, 0.36], [0.84, 0.92, 0.42]).rotation.z = -0.2;
    add(new THREE.ConeGeometry(0.38, 1.0, 4), innerEarMat, [0.98, 3.77, 0.36], [0.84, 0.92, 0.42]).rotation.z = 0.2;

    // Eyes: narrow, predatory, with a subtle vertical pupil.
    const eyeGeo = new THREE.SphereGeometry(0.16, 28, 20);
    add(eyeGeo, eyeMat, [-0.57, 2.72, 1.12], [1.85, 0.54, 0.42]);
    add(eyeGeo, eyeMat, [0.57, 2.72, 1.12], [1.85, 0.54, 0.42]);
    const pupilMat = new THREE.MeshStandardMaterial({
      color: "#020405",
      roughness: 0.26,
      metalness: 0.15,
    });
    add(new THREE.BoxGeometry(0.028, 0.19, 0.035), pupilMat, [-0.57, 2.72, 1.25], [1, 1, 1]);
    add(new THREE.BoxGeometry(0.028, 0.19, 0.035), pupilMat, [0.57, 2.72, 1.25], [1, 1, 1]);

    // Legs, joints, paws.
    const upperLeg = new THREE.CapsuleGeometry(0.37, 1.34, 10, 20);
    const lowerLeg = new THREE.CapsuleGeometry(0.29, 1.0, 10, 20);
    const legData: Array<{ x: number; z: number; lean: number }> = [
      { x: -0.82, z: 0.2, lean: 0.06 },
      { x: 0.82, z: 0.2, lean: -0.06 },
      { x: -0.58, z: -0.34, lean: 0.04 },
      { x: 0.58, z: -0.34, lean: -0.04 },
    ];

    for (const item of legData) {
      const upper = add(upperLeg, fur, [item.x, -1.12, item.z], [0.96, 1.02, 0.96]);
      upper.rotation.z = item.lean;
      const lower = add(lowerLeg, furDark, [item.x * 1.02, -2.02, item.z + 0.05], [0.92, 1.02, 0.9]);
      lower.rotation.z = item.lean * 0.5;
      add(new THREE.SphereGeometry(0.42, 32, 22), muzzleMat, [item.x * 1.02, -2.72, item.z + 0.26], [1.15, 0.52, 1.38]);
    }

    // Tail: long and heavy, curved upward like a real resting panther.
    const tailCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(1.02, -0.25, -0.45),
      new THREE.Vector3(2.0, -0.05, -0.55),
      new THREE.Vector3(2.82, 0.55, -0.58),
      new THREE.Vector3(3.12, 1.54, -0.42),
      new THREE.Vector3(2.76, 2.35, -0.22),
    ]);
    panther.add(new THREE.Mesh(
      new THREE.TubeGeometry(tailCurve, 70, 0.24, 18, false),
      fur,
    ));

    // Small whisker roots and nose bridge give the face more definition.
    add(new THREE.SphereGeometry(0.2, 24, 16), muzzleMat, [-0.31, 2.23, 1.37], [0.7, 0.45, 0.55]);
    add(new THREE.SphereGeometry(0.2, 24, 16), muzzleMat, [0.31, 2.23, 1.37], [0.7, 0.45, 0.55]);

    // Crown: restrained, dark, royal and metallic.
    const crown = new THREE.Group();
    crown.position.set(0, 4.34, 0.06);
    panther.add(crown);

    const crownBase = new THREE.Mesh(
      new THREE.CylinderGeometry(1.02, 1.22, 0.26, 48),
      crownMat,
    );
    crown.add(crownBase);

    for (let i = 0; i < 7; i++) {
      const spike = new THREE.Mesh(new THREE.ConeGeometry(0.16, 1.1, 6), crownMat);
      const angle = (i / 7) * Math.PI * 2;
      spike.position.set(Math.cos(angle) * 0.84, 0.52, Math.sin(angle) * 0.84);
      spike.scale.y = 0.92 + (i === 3 ? 0.15 : 0);
      crown.add(spike);
    }

    const crownGem = new THREE.Mesh(new THREE.IcosahedronGeometry(0.2, 1), gemMat);
    crownGem.position.set(0, 0.38, 1.03);
    crown.add(crownGem);

    const halo = new THREE.Mesh(
      new THREE.TorusGeometry(3.05, 0.045, 10, 160),
      new THREE.MeshBasicMaterial({ color: "#9cb8ca", transparent: true, opacity: 0.2 }),
    );
    halo.position.set(0, 0.85, -1.6);
    halo.rotation.x = Math.PI / 2.02;
    panther.add(halo);

    const base = new THREE.Mesh(
      new THREE.CylinderGeometry(3.55, 4.3, 0.34, 72),
      new THREE.MeshPhysicalMaterial({
        color: "#060b0f",
        metalness: 0.82,
        roughness: 0.28,
        clearcoat: 0.6,
      }),
    );
    base.position.y = -3.02;
    panther.add(base);

    // Fine fur glints: a restrained layer of short points around the silhouette.
    const furCount = window.innerWidth < 900 ? 550 : 1150;
    const furPositions = new Float32Array(furCount * 3);
    for (let i = 0; i < furCount; i++) {
      const a = Math.random() * Math.PI * 2;
      const y = -1.9 + Math.random() * 5.2;
      const width = 1.0 + Math.sin((y + 1.1) * 0.8) * 0.35 + Math.random() * 0.75;
      furPositions[i * 3] = Math.cos(a) * width;
      furPositions[i * 3 + 1] = y;
      furPositions[i * 3 + 2] = 0.38 + Math.sin(a) * 0.44;
    }
    const furGeometry = new THREE.BufferGeometry();
    furGeometry.setAttribute("position", new THREE.BufferAttribute(furPositions, 3));
    const furPoints = new THREE.Points(
      furGeometry,
      new THREE.PointsMaterial({
        color: "#202a31",
        size: 0.022,
        transparent: true,
        opacity: 0.33,
        depthWrite: false,
      }),
    );
    panther.add(furPoints);

    const pointer = { x: 0, y: 0 };
    const move = (event: PointerEvent) => {
      const rect = mount.getBoundingClientRect();
      pointer.x = (event.clientX - rect.left) / rect.width - 0.5;
      pointer.y = (event.clientY - rect.top) / rect.height - 0.5;
    };
    mount.addEventListener("pointermove", move);

    const clock = new THREE.Clock();
    let raf = 0;
    const resize = () => {
      const width = Math.max(1, mount.clientWidth);
      const height = Math.max(1, mount.clientHeight);
      camera.aspect = width / height;
      camera.fov = width > 1100 ? 32 : width > 760 ? 36 : 40;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
      starMaterial.uniforms.uPixelRatio.value = renderer.getPixelRatio();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);

    const loop = () => {
      raf = requestAnimationFrame(loop);
      const t = clock.getElapsedTime();

      const targetY = pointer.x * 0.2;
      const targetX = -pointer.y * 0.06;
      panther.rotation.y += (targetY - panther.rotation.y) * 0.018;
      panther.rotation.x += (targetX - panther.rotation.x) * 0.018;

      const breath = Math.sin(t * 1.05);
      panther.scale.y = 1 + breath * 0.008;
      panther.position.y = -2.9 + Math.sin(t * 0.72) * 0.035;
      crown.rotation.y = Math.sin(t * 0.6) * 0.025;
      crownGem.material.emissiveIntensity = 1.55 + (Math.sin(t * 1.25) + 1) * 0.3;
      solarSystem.rotation.y = t * 0.016;
      halo.rotation.z = Math.sin(t * 0.18) * 0.12;

      renderer.render(scene, camera);
    };

    resize();
    loop();

    return () => {
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      mount.removeEventListener("pointermove", move);
      starGeometry.dispose();
      starMaterial.dispose();
      furGeometry.dispose();
      renderer.dispose();
      mount.innerHTML = "";
    };
  }, []);

  return <div className="pb-space3d" ref={ref} aria-hidden="true" />;
}

export function Onboarding() {
  const { user, isPending } = useCurrentUserState();
  const complete = useSelfStore((s) => s.completeOnboarding);
  const profile = useSelfStore((s) => s.profile);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  // Once authentication has completed, enter the workspace directly.
  // The verified screen is intentionally skipped so a successful login
  // cannot leave the visitor parked on the identity gate.
  useEffect(() => {
    if (!user || profile) return;
    complete(
      user.displayName || "کاربر سلف",
      user.primaryEmail?.split("@")[0] || "salf1_user",
      "Pᴇʀsɪᴀɴ ᴮᵒᵗ · SELF",
    );
  }, [user, profile, complete]);

  if (isPending) return <div className="pb-auth pb-auth--space" dir="rtl"><SpaceRealm /><div className="pb-auth__space-vignette" /><div className="pb-auth__loading"><div className="pb-auth__loading-card"><div className="pb-seal pb-seal--loading" aria-hidden><span>P</span><i /><b /></div><p className="pb-auth__loading-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · PRIVATE</p><h1 className="pb-auth__loading-title">در حال بررسی هویت</h1><div className="pb-auth__progress" aria-hidden><span /></div><p className="pb-auth__loading-copy">لطفاً چند لحظه صبر کنید…</p></div></div></div>;

  async function handleSignIn(providerId: string) {
    setBusy(providerId); setError("");
    try { await signIn(providerId, { callbackURL: "/" }); }
    catch (err) { setError(err instanceof Error ? err.message : "ورود انجام نشد. دوباره تلاش کنید."); setBusy(null); }
  }


  if (user && profile) return (
    <div className="pb-auth" dir="rtl">
      <header className="pb-auth__top"><div className="pb-auth__brand"><div className="pb-auth__mini-seal" aria-hidden><span>P</span></div><div className="pb-auth__brand-copy"><strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong><small>پنل مدیریت سلف · PRIVATE</small></div></div><div className="pb-auth__secure"><i /><span>IDENTITY VERIFIED</span></div></header>
      <main className="pb-auth__verified"><section className="pb-auth__verified-visual"><div className="pb-seal pb-seal--verified" aria-hidden><span>P</span><i /><b /></div><p>IDENTITY VERIFIED</p></section><section className="pb-auth__card pb-auth__card--verified"><span className="pb-auth__eyebrow">AUTHENTICATION · COMPLETE</span><h1 className="pb-auth__card-title">هویت شما تأیید شد</h1><p className="pb-auth__card-desc">حساب شما با موفقیت شناسایی شد. اکنون می‌توانید وارد پنل مدیریت سلف شوید.</p><div className="pb-auth__identity"><div className="pb-auth__avatar">{user.displayName?.slice(0,1).toUpperCase() || "P"}</div><div className="pb-auth__identity-main"><strong>{user.displayName || "کاربر سلف"}</strong><span dir="ltr">{user.primaryEmail || "حساب تأییدشده"}</span></div><Check className="size-4" style={{color:"var(--pbx-green)"}} /></div><button type="button" className="pb-auth__enter">ورود به پنل مدیریت سلف<ArrowUpLeft className="size-4" /></button></section></main>
      <footer className="pb-auth__footer"><span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>پنل مدیریت سلف</span><span>Jawati · 2026</span></footer>
    </div>
  );

  return (
    <div className="pb-auth pb-auth--space" dir="rtl">
      <SpaceRealm />
      <div className="pb-auth__space-vignette" />
      <header className="pb-auth__top"><div className="pb-auth__brand"><div className="pb-auth__mini-seal" aria-hidden><span>P</span></div><div className="pb-auth__brand-copy"><strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong><small>پنل مدیریت سلف · PRIVATE SELF MANAGEMENT</small></div></div><div className="pb-auth__secure"><i /><span>PRIVATE · SECURE</span></div></header>
      <main className="pb-auth__body pb-auth__body--space">
        <section className="pb-auth__intro pb-auth__intro--space"><div className="pb-auth__intro-line"><span>01</span><i /><span>IDENTITY GATE</span></div><div className="pb-auth__hero-seal"><div className="pb-seal" aria-hidden><span>P</span><i /><b /></div></div><p className="pb-auth__intro-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · SOLAR REALM · PANTHERA</p><h1 className="pb-auth__title">هویت،<br /><em>پیش از ورود.</em></h1><p className="pb-auth__lede">ورود به یک محیط خصوصی و دقیق؛ طراحی‌شده برای مدیریت سلف با تمرکز بر اصالت هویت، آرامش بصری و تجربه‌ای یکپارچه.</p><div className="pb-auth__signature">CRAFTED BY JAWATI · @JOWATI</div></section>
        <section className="pb-auth__card pb-auth__card--space pb-auth__portal"><div className="pb-auth__portal-orbit" aria-hidden><span></span><span></span><span></span></div><div className="pb-auth__portal-core" aria-hidden><b>P</b><i></i></div><div className="pb-auth__portal-label">SECURE IDENTITY PORTAL</div><div className="pb-auth__card-head"><span className="pb-auth__eyebrow">AUTHENTICATION</span><span className="pb-auth__status"><i /> READY</span></div><h2 className="pb-auth__card-title">ورود به قلمرو سلف</h2><p className="pb-auth__card-desc">درگاه هویت فعال است. حساب خود را تأیید کنید تا ورود به محیط سه‌بعدی سلف آغاز شود.</p><div className="pb-auth__provider-list">{GROK_PROVIDERS.map((provider)=><button key={provider.providerId} type="button" className="pb-auth__provider" disabled={busy!==null} onClick={()=>handleSignIn(provider.providerId)}><span className="pb-auth__provider-mark">{provider.idp==="google"?"G":"X"}</span><span className="pb-auth__provider-copy"><strong>{busy===provider.providerId?"در حال اتصال…":"تأیید و ورود امن با "+provider.label}</strong><small>ارتباط رمزنگاری‌شده · انتقال امن به پنل</small></span><ArrowUpLeft className="pb-auth__provider-arrow size-4" /></button>)}</div>{error?<div className="pb-auth__error" role="alert">{error}</div>:null}<div className="pb-auth__divider"><span>PRIVATE ACCESS</span></div><div className="pb-auth__footnote"><ShieldCheck className="size-3.5" /><span>اطلاعات حساب شما فقط برای ایجاد یک ورود امن استفاده می‌شود.</span></div></section>
      </main>
      <footer className="pb-auth__footer"><span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>پنل مدیریت سلف</span><span>Jawati · 2026</span></footer>
    </div>
  );
}
