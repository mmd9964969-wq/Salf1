import { useEffect, useRef, useState } from "react";
import { ArrowUpLeft, ShieldCheck } from "lucide-react";
import { GROK_PROVIDERS } from "@/lib/auth/providers";
import { signIn } from "@/lib/auth/client";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { useSelfStore } from "@/lib/store";
import * as THREE from "three";
import "@/styles/persian-bot-auth.css";

function SolarRealm() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = ref.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#01050a");
    scene.fog = new THREE.FogExp2("#02070c", 0.008);

    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 500);
    camera.position.set(0, 1.2, 18);

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    mount.appendChild(renderer.domElement);

    const ambient = new THREE.HemisphereLight("#bcd2df", "#010203", 1.1);
    scene.add(ambient);
    const key = new THREE.DirectionalLight("#e4f2fa", 3.2);
    key.position.set(-7, 8, 9);
    scene.add(key);
    const rim = new THREE.PointLight("#80c9ef", 14, 34, 2);
    rim.position.set(5, 3, 5);
    scene.add(rim);

    const starCount = window.innerWidth < 700 ? 650 : 1350;
    const positions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      const r = 45 + Math.random() * 170;
      const a = Math.random() * Math.PI * 2;
      positions[i * 3] = Math.cos(a) * r;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 100;
      positions[i * 3 + 2] = Math.sin(a) * r - 55;
    }
    const starsGeo = new THREE.BufferGeometry();
    starsGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const stars = new THREE.Points(
      starsGeo,
      new THREE.PointsMaterial({ color: "#b9d9ea", size: 0.045, transparent: true, opacity: 0.72, depthWrite: false }),
    );
    scene.add(stars);

    const system = new THREE.Group();
    scene.add(system);

    const sun = new THREE.Mesh(
      new THREE.SphereGeometry(1.55, 48, 32),
      new THREE.MeshStandardMaterial({ color: "#d5a05a", emissive: "#754714", emissiveIntensity: 2.6, roughness: 0.72 }),
    );
    sun.position.set(-8.5, 5.4, -24);
    system.add(sun);

    [3.8, 5.7, 7.4].forEach((radius, index) => {
      const orbit = new THREE.Mesh(
        new THREE.TorusGeometry(radius, 0.012, 8, 220),
        new THREE.MeshBasicMaterial({ color: "#9eb8c8", transparent: true, opacity: 0.12 - index * 0.02 }),
      );
      orbit.position.copy(sun.position);
      orbit.rotation.x = Math.PI / 2.2;
      system.add(orbit);

      const planet = new THREE.Mesh(
        new THREE.SphereGeometry([0.18, 0.28, 0.4][index], 24, 18),
        new THREE.MeshStandardMaterial({ color: ["#6f8797", "#8c654d", "#8a969d"][index], roughness: 0.9 }),
      );
      planet.position.set(sun.position.x + radius, sun.position.y, sun.position.z);
      system.add(planet);
    });

    // Stage 1 intentionally uses a restrained silhouette placeholder.
    // The production photorealistic Panthera GLB is mounted in the asset stage.
    const panther = new THREE.Group();
    panther.position.set(0, -2.35, 0);
    scene.add(panther);

    const black = new THREE.MeshPhysicalMaterial({ color: "#020405", roughness: 0.38, metalness: 0.12, clearcoat: 0.35 });
    const silver = new THREE.MeshPhysicalMaterial({ color: "#9fa8ae", metalness: 0.96, roughness: 0.16, clearcoat: 0.75 });
    const eye = new THREE.MeshStandardMaterial({ color: "#dff5ff", emissive: "#72c8f2", emissiveIntensity: 4.5 });

    const add = (geometry: THREE.BufferGeometry, material: THREE.Material, p: [number, number, number], s: [number, number, number]) => {
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(...p);
      mesh.scale.set(...s);
      panther.add(mesh);
      return mesh;
    };

    add(new THREE.SphereGeometry(1.7, 48, 32), black, [0, -0.2, 0], [1.15, 1.45, 0.78]);
    add(new THREE.SphereGeometry(1.25, 40, 28), black, [0, 2.05, 0.12], [0.96, 1.05, 0.88]);
    add(new THREE.SphereGeometry(0.55, 32, 24), black, [0, 1.42, 0.75], [1.15, 0.65, 0.72]);
    add(new THREE.SphereGeometry(0.14, 24, 18), eye, [-0.48, 2.18, 0.84], [1.8, 0.55, 0.35]);
    add(new THREE.SphereGeometry(0.14, 24, 18), eye, [0.48, 2.18, 0.84], [1.8, 0.55, 0.35]);

    const crown = new THREE.Group();
    crown.position.y = 3.55;
    panther.add(crown);
    crown.add(new THREE.Mesh(new THREE.CylinderGeometry(0.92, 1.08, 0.24, 40), silver));
    for (let i = 0; i < 7; i++) {
      const spike = new THREE.Mesh(new THREE.ConeGeometry(0.13, 0.9, 6), silver);
      const a = (i / 7) * Math.PI * 2;
      spike.position.set(Math.cos(a) * 0.72, 0.48, Math.sin(a) * 0.72);
      crown.add(spike);
    }

    const pointer = { x: 0, y: 0 };
    const onPointer = (event: PointerEvent) => {
      const rect = mount.getBoundingClientRect();
      pointer.x = (event.clientX - rect.left) / rect.width - 0.5;
      pointer.y = (event.clientY - rect.top) / rect.height - 0.5;
    };
    mount.addEventListener("pointermove", onPointer);

    const resize = () => {
      const width = Math.max(1, mount.clientWidth);
      const height = Math.max(1, mount.clientHeight);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    const clock = new THREE.Clock();
    let raf = 0;
    const animate = () => {
      raf = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();
      panther.rotation.y += (pointer.x * 0.24 - panther.rotation.y) * 0.018;
      panther.rotation.x += (-pointer.y * 0.05 - panther.rotation.x) * 0.018;
      panther.position.y = -2.35 + Math.sin(t * 0.72) * 0.035;
      panther.scale.y = 1 + Math.sin(t * 1.05) * 0.007;
      crown.rotation.y = Math.sin(t * 0.6) * 0.025;
      system.rotation.y = t * 0.012;
      renderer.render(scene, camera);
    };

    resize();
    animate();

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      mount.removeEventListener("pointermove", onPointer);
      starsGeo.dispose();
      (stars.material as THREE.Material).dispose();
      renderer.dispose();
      mount.replaceChildren();
    };
  }, []);

  return <div ref={ref} className="pb-space3d" aria-hidden="true" />;
}

export function Onboarding() {
  const { user, isPending } = useCurrentUserState();
  const complete = useSelfStore((s) => s.completeOnboarding);
  const profile = useSelfStore((s) => s.profile);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user || profile) return;
    complete(
      user.displayName || "کاربر سلف",
      user.primaryEmail?.split("@")[0] || "salf1_user",
      "Pᴇʀsɪᴀɴ ᴮᵒᵗ · SELF",
    );
  }, [user, profile, complete]);

  async function handleSignIn(providerId: string) {
    setBusy(providerId);
    setError("");
    try {
      await signIn(providerId, { callbackURL: "/" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "ورود انجام نشد. دوباره تلاش کنید.");
      setBusy(null);
    }
  }

  if (isPending) {
    return (
      <div className="pb-auth pb-auth--space" dir="rtl">
        <SolarRealm />
        <div className="pb-auth__space-vignette" />
        <div className="pb-auth__loading">
          <div className="pb-auth__loading-card">
            <div className="pb-seal pb-seal--loading" aria-hidden><span>P</span><i /><b /></div>
            <p className="pb-auth__loading-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · PRIVATE</p>
            <h1 className="pb-auth__loading-title">در حال بررسی هویت</h1>
            <div className="pb-auth__progress" aria-hidden><span /></div>
            <p className="pb-auth__loading-copy">لطفاً چند لحظه صبر کنید…</p>
          </div>
        </div>
      </div>
    );
  }

  if (user && profile) {
    return <div className="pb-auth pb-auth--space" dir="rtl"><SolarRealm /><div className="pb-auth__space-vignette" /></div>;
  }

  return (
    <div className="pb-auth pb-auth--space" dir="rtl">
      <SolarRealm />
      <div className="pb-auth__space-vignette" />
      <header className="pb-auth__top">
        <div className="pb-auth__brand">
          <div className="pb-auth__mini-seal" aria-hidden><span>P</span></div>
          <div className="pb-auth__brand-copy">
            <strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong>
            <small>SALF1 · PRIVATE MANAGEMENT REALM</small>
          </div>
        </div>
        <div className="pb-auth__secure"><i /><span>SECURE IDENTITY GATE</span></div>
      </header>

      <main className="pb-auth__body pb-auth__body--space">
        <section className="pb-auth__intro pb-auth__intro--space">
          <div className="pb-auth__intro-line"><span>01</span><i /><span>IDENTITY GATE</span></div>
          <p className="pb-auth__intro-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · PANTHERA REALM</p>
          <h1 className="pb-auth__title">هویت،<br /><em>پیش از ورود.</em></h1>
          <p className="pb-auth__lede">درگاه ورود به قلمرو خصوصی سلف؛ آرام، دقیق و ساخته‌شده برای تجربه‌ای سه‌بعدی.</p>
          <div className="pb-auth__signature">CRAFTED BY JAWATI · @JOWATI</div>
        </section>

        <section className="pb-auth__card pb-auth__card--space pb-auth__portal">
          <div className="pb-auth__portal-orbit" aria-hidden><span /><span /><span /></div>
          <div className="pb-auth__portal-core" aria-hidden><b>P</b><i /></div>
          <div className="pb-auth__portal-label">SECURE IDENTITY PORTAL</div>
          <div className="pb-auth__card-head"><span className="pb-auth__eyebrow">AUTHENTICATION</span><span className="pb-auth__status"><i /> READY</span></div>
          <h2 className="pb-auth__card-title">ورود به قلمرو سلف</h2>
          <p className="pb-auth__card-desc">حساب خود را تأیید کنید تا ورود امن به محیط SALF1 آغاز شود.</p>
          <div className="pb-auth__provider-list">
            {GROK_PROVIDERS.map((provider) => (
              <button key={provider.providerId} type="button" className="pb-auth__provider" disabled={busy !== null} onClick={() => handleSignIn(provider.providerId)}>
                <span className="pb-auth__provider-mark">{provider.idp === "google" ? "G" : "X"}</span>
                <span className="pb-auth__provider-copy">
                  <strong>{busy === provider.providerId ? "در حال اتصال…" : "تأیید و ورود امن با " + provider.label}</strong>
                  <small>ارتباط رمزنگاری‌شده · انتقال امن</small>
                </span>
                <ArrowUpLeft className="pb-auth__provider-arrow size-4" />
              </button>
            ))}
          </div>
          {error ? <div className="pb-auth__error" role="alert">{error}</div> : null}
          <div className="pb-auth__divider"><span>PRIVATE ACCESS</span></div>
          <div className="pb-auth__footnote"><ShieldCheck className="size-3.5" /><span>اطلاعات حساب فقط برای ایجاد یک ورود امن استفاده می‌شود.</span></div>
        </section>
      </main>

      <footer className="pb-auth__footer"><span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>SALF1 · PANTHERA REALM</span><span>JAWATI · 2026</span></footer>
    </div>
  );
}
