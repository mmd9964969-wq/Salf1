import { useEffect, useRef, useState } from "react";
import { ArrowUpLeft, ShieldCheck } from "lucide-react";
import { GROK_PROVIDERS } from "@/lib/auth/providers";
import { signIn } from "@/lib/auth/client";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import { useSelfStore } from "@/lib/store";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import "@/styles/persian-bot-auth.css";

function SolarRealm() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = ref.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#010307");
    scene.fog = new THREE.FogExp2("#010307", 0.0038);

    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 900);
    camera.position.set(0, 2.3, 22);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.65));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    const world = new THREE.Group();
    scene.add(world);

    // Deep-space star field with multiple depth layers.
    const makeStars = (count: number, radiusMin: number, radiusMax: number, size: number, opacity: number) => {
      const positions = new Float32Array(count * 3);
      for (let i = 0; i < count; i++) {
        const r = radiusMin + Math.random() * (radiusMax - radiusMin);
        const a = Math.random() * Math.PI * 2;
        const y = (Math.random() - 0.5) * radiusMax * 0.72;
        positions[i * 3] = Math.cos(a) * r;
        positions[i * 3 + 1] = y;
        positions[i * 3 + 2] = Math.sin(a) * r - 70;
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      const material = new THREE.PointsMaterial({
        color: "#d6ecf8",
        size,
        transparent: true,
        opacity,
        depthWrite: false,
      });
      return new THREE.Points(geometry, material);
    };

    const starsFar = makeStars(window.innerWidth < 700 ? 900 : 2100, 70, 320, 0.055, 0.62);
    const starsNear = makeStars(window.innerWidth < 700 ? 280 : 650, 35, 130, 0.09, 0.38);
    world.add(starsFar, starsNear);

    // Soft procedural galaxy disc.
    const galaxyGeometry = new THREE.BufferGeometry();
    const galaxyCount = window.innerWidth < 700 ? 9000 : 18000;
    const galaxyPositions = new Float32Array(galaxyCount * 3);
    const galaxyColors = new Float32Array(galaxyCount * 3);
    const color = new THREE.Color();
    for (let i = 0; i < galaxyCount; i++) {
      const arm = i % 4;
      const radius = Math.pow(Math.random(), 0.62) * 115;
      const angle = radius * 0.085 + arm * (Math.PI / 2) + (Math.random() - 0.5) * 0.65;
      const spread = (Math.random() - 0.5) * (3 + radius * 0.035);
      galaxyPositions[i * 3] = Math.cos(angle) * radius + spread;
      galaxyPositions[i * 3 + 1] = (Math.random() - 0.5) * (2.4 + radius * 0.015);
      galaxyPositions[i * 3 + 2] = Math.sin(angle) * radius - 95 + spread;
      color.setHSL(0.54 + Math.random() * 0.07, 0.34, 0.5 + Math.random() * 0.32);
      galaxyColors[i * 3] = color.r;
      galaxyColors[i * 3 + 1] = color.g;
      galaxyColors[i * 3 + 2] = color.b;
    }
    galaxyGeometry.setAttribute("position", new THREE.BufferAttribute(galaxyPositions, 3));
    galaxyGeometry.setAttribute("color", new THREE.BufferAttribute(galaxyColors, 3));
    const galaxy = new THREE.Points(
      galaxyGeometry,
      new THREE.PointsMaterial({
        size: 0.075,
        vertexColors: true,
        transparent: true,
        opacity: 0.36,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    );
    galaxy.rotation.x = 0.42;
    galaxy.position.set(0, -18, -70);
    world.add(galaxy);

    // Cinematic lighting.
    scene.add(new THREE.HemisphereLight("#cfe8f5", "#020305", 0.55));
    const solarLight = new THREE.PointLight("#fff1d0", 70, 150, 2);
    solarLight.position.set(-16, 9, -40);
    solarLight.castShadow = true;
    solarLight.shadow.mapSize.set(1024, 1024);
    world.add(solarLight);

    const coldRim = new THREE.DirectionalLight("#8fd6ff", 4.2);
    coldRim.position.set(14, 8, 8);
    world.add(coldRim);

    const silverRim = new THREE.PointLight("#b8e7ff", 24, 70, 2);
    silverRim.position.set(5, 5, 6);
    world.add(silverRim);

    // Sun with layered glow.
    const solarSystem = new THREE.Group();
    solarSystem.position.set(-11, 4.7, -42);
    world.add(solarSystem);

    const sun = new THREE.Mesh(
      new THREE.SphereGeometry(2.45, 64, 48),
      new THREE.MeshStandardMaterial({
        color: "#e5a85f",
        emissive: "#8a4614",
        emissiveIntensity: 4.8,
        roughness: 0.72,
      }),
    );
    solarSystem.add(sun);

    for (let i = 0; i < 5; i++) {
      const glow = new THREE.Mesh(
        new THREE.SphereGeometry(2.8 + i * 0.42, 48, 32),
        new THREE.MeshBasicMaterial({
          color: i % 2 ? "#d8873c" : "#f0bb75",
          transparent: true,
          opacity: 0.055 - i * 0.008,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        }),
      );
      solarSystem.add(glow);
    }

    const planetData = [
      [4.3, 0.22, "#8e9aa0", 0.08],
      [6.4, 0.34, "#b18c69", -0.05],
      [8.6, 0.46, "#718d9e", 0.03],
      [11.2, 0.58, "#9c8067", -0.025],
      [14.3, 0.92, "#b4a17c", 0.012],
      [18.1, 0.67, "#6f8898", -0.009],
    ] as const;

    const orbitGroups: THREE.Group[] = [];
    planetData.forEach(([radius, size, tint, speed], index) => {
      const orbit = new THREE.Group();
      solarSystem.add(orbit);
      orbitGroups.push(orbit);

      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(radius, 0.008 + index * 0.002, 8, 240),
        new THREE.MeshBasicMaterial({
          color: "#9bb6c7",
          transparent: true,
          opacity: 0.12,
        }),
      );
      ring.rotation.x = Math.PI / 2.04;
      solarSystem.add(ring);

      const planet = new THREE.Mesh(
        new THREE.SphereGeometry(size, 36, 24),
        new THREE.MeshStandardMaterial({
          color: tint,
          roughness: 0.82,
          metalness: 0.04,
        }),
      );
      planet.position.x = radius;
      planet.castShadow = true;
      orbit.add(planet);

      if (index === 2 || index === 4) {
        const planetRing = new THREE.Mesh(
          new THREE.TorusGeometry(size * 1.55, size * 0.045, 10, 100),
          new THREE.MeshBasicMaterial({
            color: "#b6c8d1",
            transparent: true,
            opacity: 0.32,
          }),
        );
        planetRing.rotation.x = Math.PI / 2.3;
        planet.add(planetRing);
      }

      orbit.userData.speed = speed;
      orbit.rotation.y = index * 0.8;
    });

    // Asteroid belt.
    const asteroidGeometry = new THREE.BufferGeometry();
    const asteroidCount = window.innerWidth < 700 ? 420 : 950;
    const asteroidPositions = new Float32Array(asteroidCount * 3);
    for (let i = 0; i < asteroidCount; i++) {
      const radius = 21.5 + Math.random() * 4.6;
      const a = Math.random() * Math.PI * 2;
      asteroidPositions[i * 3] = Math.cos(a) * radius;
      asteroidPositions[i * 3 + 1] = (Math.random() - 0.5) * 1.7;
      asteroidPositions[i * 3 + 2] = Math.sin(a) * radius;
    }
    asteroidGeometry.setAttribute("position", new THREE.BufferAttribute(asteroidPositions, 3));
    solarSystem.add(
      new THREE.Points(
        asteroidGeometry,
        new THREE.PointsMaterial({
          color: "#aab4b9",
          size: 0.075,
          transparent: true,
          opacity: 0.42,
        }),
      ),
    );

    // Real model slot: the production asset must be a real, licensed, rigged GLB.
    const pantherRoot = new THREE.Group();
    pantherRoot.position.set(1.8, -1.7, 1.1);
    pantherRoot.scale.setScalar(2.55);
    world.add(pantherRoot);

    const crown = new THREE.Group();
    const silver = new THREE.MeshPhysicalMaterial({
      color: "#b8c2c8",
      metalness: 0.98,
      roughness: 0.16,
      clearcoat: 0.82,
      clearcoatRoughness: 0.12,
    });
    crown.add(new THREE.Mesh(new THREE.CylinderGeometry(0.43, 0.5, 0.12, 48), silver));
    for (let i = 0; i < 7; i++) {
      const spike = new THREE.Mesh(new THREE.ConeGeometry(0.065, 0.48, 8), silver);
      const a = (i / 7) * Math.PI * 2;
      spike.position.set(Math.cos(a) * 0.34, 0.27, Math.sin(a) * 0.34);
      crown.add(spike);
    }
    crown.visible = false;
    pantherRoot.add(crown);

    const loader = new GLTFLoader();
    let mixer: THREE.AnimationMixer | null = null;
    let model: THREE.Object3D | null = null;
    let loadCancelled = false;

    loader.load(
      "/assets/panther/panther.glb",
      (gltf) => {
        if (loadCancelled) return;
        model = gltf.scene;
        model.traverse((node) => {
          if (node instanceof THREE.Mesh) {
            node.castShadow = true;
            node.receiveShadow = true;
            if (node.material instanceof THREE.MeshStandardMaterial || node.material instanceof THREE.MeshPhysicalMaterial) {
              node.material.roughness = Math.max(0.48, node.material.roughness);
            }
          }
        });

        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        model.position.sub(center);
        const maxAxis = Math.max(size.x, size.y, size.z);
        const normalized = 3.2 / Math.max(maxAxis, 0.001);
        model.scale.setScalar(normalized);
        pantherRoot.add(model);

        crown.visible = true;
        crown.position.set(0, 1.72, 0);

        if (gltf.animations.length) {
          mixer = new THREE.AnimationMixer(model);
          const preferred = gltf.animations.find((clip) => /walk|idle|stand/i.test(clip.name)) ?? gltf.animations[0];
          mixer.clipAction(preferred).play();
        }
      },
      undefined,
      () => {
        // Do not substitute a cartoon primitive. Until the licensed GLB exists,
        // the page intentionally keeps the panther slot empty rather than faking realism.
      },
    );

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
      renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    const clock = new THREE.Clock();
    let raf = 0;
    const animate = () => {
      raf = requestAnimationFrame(animate);
      const dt = clock.getDelta();
      const t = clock.elapsedTime;

      starsFar.rotation.y = t * 0.0014;
      starsNear.rotation.y = -t * 0.0021;
      galaxy.rotation.y = t * 0.0032;
      solarSystem.rotation.y = t * 0.005;
      solarSystem.rotation.x = Math.sin(t * 0.08) * 0.035;

      orbitGroups.forEach((orbit) => {
        orbit.rotation.y += Number(orbit.userData.speed) * 0.002;
      });

      if (model) {
        const roamX = Math.sin(t * 0.085) * 2.8;
        const roamZ = Math.cos(t * 0.065) * 1.9;
        pantherRoot.position.x += (1.8 + roamX - pantherRoot.position.x) * 0.012;
        pantherRoot.position.z += (1.1 + roamZ - pantherRoot.position.z) * 0.012;
        pantherRoot.rotation.y = Math.atan2(roamX - Math.sin((t - 0.08) * 0.085) * 2.8, roamZ - Math.cos((t - 0.08) * 0.065) * 1.9);
        pantherRoot.rotation.y += pointer.x * 0.14;
        pantherRoot.position.y = -1.7 + Math.sin(t * 1.9) * 0.018;
        mixer?.update(dt);
      }

      camera.position.x += (pointer.x * 1.15 - camera.position.x) * 0.015;
      camera.position.y += (2.3 - pointer.y * 0.55 - camera.position.y) * 0.015;
      camera.lookAt(0, 0.2, -13);

      renderer.render(scene, camera);
    };

    resize();
    animate();

    return () => {
      loadCancelled = true;
      cancelAnimationFrame(raf);
      observer.disconnect();
      mount.removeEventListener("pointermove", onPointer);
      mixer?.stopAllAction();
      galaxyGeometry.dispose();
      asteroidGeometry.dispose();
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
            <h1 className="pb-auth__loading-title">در حال ورود به قلمرو</h1>
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
          <p className="pb-auth__lede">درگاه ورود به قلمرو خصوصی سلف؛ یک تجربه سه‌بعدی سینمایی با منظومه شمسی، کهکشان و هویت Panthera.</p>
          <div className="pb-auth__signature">CRAFTED BY JAWATI · @JOWATI</div>
        </section>

        <section className="pb-auth__card pb-auth__card--space pb-auth__portal">
          <div className="pb-auth__portal-orbit" aria-hidden><span /><span /><span /></div>
          <div className="pb-auth__portal-core" aria-hidden><b>P</b><i /></div>
          <div className="pb-auth__portal-label">SECURE IDENTITY PORTAL</div>
          <div className="pb-auth__card-head"><span className="pb-auth__eyebrow">AUTHENTICATION</span><span className="pb-auth__status"><i /> READY</span></div>
          <h2 className="pb-auth__card-title">ورود به قلمرو سلف</h2>
          <p className="pb-auth__card-desc">حساب خود را تأیید کنید تا ورود امن به محیط SALF1 آغاز شود؛ قلمرو سه‌بعدی در حال شکل‌گیری است.</p>
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
