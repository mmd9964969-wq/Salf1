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

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.65));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    const world = new THREE.Group();
    scene.add(world);

    const makeStars = (count: number, radiusMin: number, radiusMax: number, size: number, opacity: number) => {
      const positions = new Float32Array(count * 3);
      for (let i = 0; i < count; i++) {
        const r = radiusMin + Math.random() * (radiusMax - radiusMin);
        const a = Math.random() * Math.PI * 2;
        positions[i * 3] = Math.cos(a) * r;
        positions[i * 3 + 1] = (Math.random() - 0.5) * radiusMax * 0.72;
        positions[i * 3 + 2] = Math.sin(a) * r - 70;
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      return new THREE.Points(geometry, new THREE.PointsMaterial({
        color: "#d6ecf8", size, transparent: true, opacity, depthWrite: false,
      }));
    };

    const starsFar = makeStars(window.innerWidth < 700 ? 900 : 2100, 70, 320, 0.055, 0.62);
    const starsNear = makeStars(window.innerWidth < 700 ? 280 : 650, 35, 130, 0.09, 0.38);
    world.add(starsFar, starsNear);

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
    const galaxy = new THREE.Points(galaxyGeometry, new THREE.PointsMaterial({
      size: 0.075, vertexColors: true, transparent: true, opacity: 0.36,
      depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    galaxy.rotation.x = 0.42;
    galaxy.position.set(0, -18, -70);
    world.add(galaxy);

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

    const solarSystem = new THREE.Group();
    solarSystem.position.set(-11, 4.7, -42);
    world.add(solarSystem);

    const sun = new THREE.Mesh(
      new THREE.SphereGeometry(2.45, 64, 48),
      new THREE.MeshStandardMaterial({ color: "#e5a85f", emissive: "#8a4614", emissiveIntensity: 4.8, roughness: 0.72 }),
    );
    solarSystem.add(sun);

    for (let i = 0; i < 5; i++) {
      solarSystem.add(new THREE.Mesh(
        new THREE.SphereGeometry(2.8 + i * 0.42, 48, 32),
        new THREE.MeshBasicMaterial({
          color: i % 2 ? "#d8873c" : "#f0bb75",
          transparent: true, opacity: 0.055 - i * 0.008,
          blending: THREE.AdditiveBlending, depthWrite: false,
        }),
      ));
    }

    // HD procedural planet detail: layered relief, cloud shells, atmospheric rims and moons.
    const planetDetail = (tint: string, seed: number) => {
      const canvas = document.createElement("canvas"); canvas.width = 512; canvas.height = 256;
      const ctx = canvas.getContext("2d"); if (!ctx) return null;
      const image = ctx.createImageData(canvas.width, canvas.height); const data = image.data;
      const base = new THREE.Color(tint);
      for (let y = 0; y < canvas.height; y++) for (let x = 0; x < canvas.width; x++) {
        const i = (y * canvas.width + x) * 4;
        const n = (Math.sin(x * 0.047 + seed) + Math.sin(y * 0.083 - seed * 1.7) + Math.sin((x+y) * 0.021)) / 3;
        const v = THREE.MathUtils.clamp(0.78 + n * 0.22, 0.45, 1.05);
        data[i] = Math.min(255, base.r * 255 * v); data[i+1] = Math.min(255, base.g * 255 * v); data[i+2] = Math.min(255, base.b * 255 * v); data[i+3] = 255;
      }
      ctx.putImageData(image,0,0); const tex = new THREE.CanvasTexture(canvas); tex.colorSpace=THREE.SRGBColorSpace; tex.anisotropy=4; return tex;
    };
    const addAtmosphere = (planet: THREE.Mesh, radius: number, color: string, opacity: number) => {
      const shell = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.055, 48, 32), new THREE.MeshBasicMaterial({color, transparent:true, opacity, side:THREE.BackSide, blending:THREE.AdditiveBlending, depthWrite:false}));
      planet.add(shell);
    };
    const moonMaterial = new THREE.MeshStandardMaterial({color:"#9da5a9", roughness:0.92, metalness:0.0});
    const moonSpecs = [[2,1.05,0.13,0.9],[4,1.25,0.17,0.65],[5,1.45,0.12,1.15]] as const;
    moonSpecs.forEach(([parentIndex, orbitRadius, moonSize, speed]) => {
      const parent = orbitGroups[parentIndex]; if (!parent) return;
      const moonOrbit = new THREE.Group(); parent.add(moonOrbit); moonOrbit.userData.moonSpeed=speed;
      const moon = new THREE.Mesh(new THREE.SphereGeometry(moonSize,24,16), moonMaterial.clone()); moon.position.x=orbitRadius; moon.castShadow=true; moonOrbit.add(moon);
    });

\n    const planetData = [
      [4.3, 0.22, "#8e9aa0", 0.08], [6.4, 0.34, "#b18c69", -0.05],
      [8.6, 0.46, "#718d9e", 0.03], [11.2, 0.58, "#9c8067", -0.025],
      [14.3, 0.92, "#b4a17c", 0.012], [18.1, 0.67, "#6f8898", -0.009],
    ] as const;
    const orbitGroups: THREE.Group[] = [];

    planetData.forEach(([radius, size, tint, speed], index) => {
      const orbit = new THREE.Group();
      solarSystem.add(orbit);
      orbitGroups.push(orbit);

      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(radius, 0.008 + index * 0.002, 8, 240),
        new THREE.MeshBasicMaterial({ color: "#9bb6c7", transparent: true, opacity: 0.12 }),
      );
      ring.rotation.x = Math.PI / 2.04;
      solarSystem.add(ring);

      const planet = new THREE.Mesh(
        new THREE.SphereGeometry(size, 36, 24),
        new THREE.MeshStandardMaterial({ color: tint, roughness: 0.82, metalness: 0.04 }),
      );
      planet.position.x = radius;
      planet.castShadow = true;
      orbit.add(planet);

      if (index === 2 || index === 4) {
        const planetRing = new THREE.Mesh(
          new THREE.TorusGeometry(size * 1.55, size * 0.045, 10, 100),
          new THREE.MeshBasicMaterial({ color: "#b6c8d1", transparent: true, opacity: 0.32 }),
        );
        planetRing.rotation.x = Math.PI / 2.3;
        planet.add(planetRing);
      }
      if (index === 2 || index === 5) addAtmosphere(planet, size, index === 2 ? "#6ea9d8" : "#6e9bb8", 0.11);\n      orbit.userData.speed = speed;
      orbit.rotation.y = index * 0.8;
    });

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
    solarSystem.add(new THREE.Points(
      asteroidGeometry,
      new THREE.PointsMaterial({ color: "#aab4b9", size: 0.075, transparent: true, opacity: 0.42 }),
    ));

    const pantherRoot = new THREE.Group();
    pantherRoot.position.set(1.8, -1.7, 1.1);
    pantherRoot.scale.setScalar(2.55);
    world.add(pantherRoot);

    const crown = new THREE.Group();
    const silver = new THREE.MeshPhysicalMaterial({
      color: "#b8c2c8", metalness: 0.98, roughness: 0.16, clearcoat: 0.82, clearcoatRoughness: 0.12,
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
    let activeAction: THREE.AnimationAction | null = null;
    let model: THREE.Object3D | null = null;
    let loadCancelled = false;

    const findClip = (clips: THREE.AnimationClip[], patterns: RegExp[]) =>
      clips.find((clip) => patterns.some((pattern) => pattern.test(clip.name)));

    const playAction = (clip: THREE.AnimationClip | undefined, fade = 0.45) => {
      if (!mixer || !clip || activeAction?.getClip() === clip) return;
      const next = mixer.clipAction(clip);
      next.reset().fadeIn(fade).play();
      activeAction?.fadeOut(fade);
      activeAction = next;
    };

    type PantherRig = {
      spine: THREE.Bone | null;
      chest: THREE.Bone | null;
      neck: THREE.Bone | null;
      head: THREE.Bone | null;
      jaw: THREE.Bone | null;
      ears: THREE.Bone[];
      tail: THREE.Bone[];
      frontLegs: THREE.Bone[][];
      rearLegs: THREE.Bone[][];
      eyelids: THREE.Bone[];
      lastRot: Map<THREE.Bone, THREE.Quaternion>;
      lastPos: Map<THREE.Bone, THREE.Vector3>;
    };

    const buildPantherRig = (root: THREE.Object3D): PantherRig => {
      const bones: THREE.Bone[] = [];
      root.traverse((node) => {
        if (node instanceof THREE.Bone) bones.push(node);
      });

      const pick = (patterns: RegExp[]) =>
        bones.find((bone) => patterns.some((pattern) => pattern.test(bone.name))) ?? null;

      const pickMany = (patterns: RegExp[]) =>
        bones.filter((bone) => patterns.some((pattern) => pattern.test(bone.name)));

      const left = (name: string) => /(^|[_ .-])l(eft)?($|[_ .-])/i.test(name) || /left|_l\b/i.test(name);
      const right = (name: string) => /(^|[_ .-])r(ight)?($|[_ .-])/i.test(name) || /right|_r\b/i.test(name);

      const front = bones.filter((bone) => /front|fore|shoulder|upperarm|forearm|wrist|paw/i.test(bone.name));
      const rear = bones.filter((bone) => /hind|rear|thigh|calf|ankle|hock|paw/i.test(bone.name));

      const groupSide = (source: THREE.Bone[], side: "left" | "right") => {
        const matcher = side === "left" ? left : right;
        return source.filter((bone) => matcher(bone.name));
      };

      const frontLeft = groupSide(front, "left").slice(0, 5);
      const frontRight = groupSide(front, "right").slice(0, 5);
      const rearLeft = groupSide(rear, "left").slice(0, 5);
      const rearRight = groupSide(rear, "right").slice(0, 5);

      return {
        spine: pick([/spine/i, /back/i, /body/i]),
        chest: pick([/chest/i, /rib/i, /thorax/i]),
        neck: pick([/neck/i]),
        head: pick([/head/i, /skull/i]),
        jaw: pick([/jaw/i, /mandible/i, /mouth/i]),
        ears: pickMany([/ear/i, /pinna/i]).slice(0, 2),
        tail: pickMany([/tail/i, /caudal/i]).slice(0, 8),
        frontLegs: [frontLeft, frontRight],
        rearLegs: [rearLeft, rearRight],
        eyelids: pickMany([/eyelid/i, /lid/i]).slice(0, 4),
        lastRot: new Map(),
        lastPos: new Map(),
      };
    };

    const applyPantherBehavior = (rig: PantherRig, t: number, moving: boolean, stalking: boolean) => {
      const applyRotation = (bone: THREE.Bone | undefined | null, x: number, y: number, z: number) => {
        if (!bone) return;
        const previous = rig.lastRot.get(bone);
        if (previous) bone.quaternion.multiply(previous.clone().invert());
        const delta = new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z));
        bone.quaternion.multiply(delta);
        rig.lastRot.set(bone, delta);
      };

      const applyPosition = (bone: THREE.Bone | undefined | null, x: number, y: number, z: number) => {
        if (!bone) return;
        const previous = rig.lastPos.get(bone);
        if (previous) bone.position.sub(previous);
        const delta = new THREE.Vector3(x, y, z);
        bone.position.add(delta);
        rig.lastPos.set(bone, delta);
      };

      const breathe = Math.sin(t * 1.65) * 0.028 + Math.sin(t * 0.83) * 0.012;
      applyRotation(rig.chest ?? rig.spine, breathe, 0, 0);
      applyPosition(rig.chest ?? rig.spine, 0, Math.sin(t * 1.65) * 0.006, 0);

      const headScan = Math.sin(t * 0.31) * 0.12 + Math.sin(t * 0.77) * 0.035;
      const headLift = stalking ? -0.065 : 0.018 + Math.sin(t * 0.23) * 0.02;
      applyRotation(rig.neck, headLift * 0.35, headScan * 0.35, 0);
      applyRotation(rig.head, headLift, headScan, Math.sin(t * 0.42) * 0.02);

      const earTurn = Math.sin(t * 1.7) * 0.08 + Math.sin(t * 0.57) * 0.035;
      rig.ears.forEach((ear, index) => {
        const side = index % 2 === 0 ? 1 : -1;
        applyRotation(ear, Math.sin(t * 1.1 + index) * 0.045, side * (earTurn * 0.35), side * 0.06);
      });

      if (rig.jaw) {
        const jawPulse = Math.max(0, Math.sin(t * 0.21)) * 0.012;
        applyRotation(rig.jaw, jawPulse, 0, 0);
      }

      const tailWave = Math.sin(t * (moving ? 2.2 : 1.1)) * (moving ? 0.16 : 0.09);
      rig.tail.forEach((bone, index) => {
        const weight = 1 - index / Math.max(1, rig.tail.length);
        applyRotation(bone, 0, tailWave * weight, Math.sin(t * 1.3 + index * 0.7) * 0.045 * weight);
      });

      const gait = moving ? t * (stalking ? 4.7 : 6.1) : 0;
      const gaitPhase = gait % (Math.PI * 2);
      const stride = stalking ? 0.22 : 0.34;
      const lift = stalking ? 0.06 : 0.11;
      const legSets = [...rig.frontLegs, ...rig.rearLegs];
      legSets.forEach((chain, legIndex) => {
        const sidePhase = legIndex % 2 === 0 ? 0 : Math.PI;
        chain.slice(0, 2).forEach((bone, jointIndex) => {
          const phase = gaitPhase + sidePhase + jointIndex * 0.34;
          const swing = Math.sin(phase) * stride * (jointIndex === 0 ? 0.65 : 1);
          const raise = Math.max(0, Math.sin(phase + Math.PI * 0.12)) * lift;
          applyRotation(bone, swing, 0, 0);
          applyPosition(bone, 0, raise * (jointIndex === 0 ? 0.45 : 0.2), 0);
        });
      });

      const blinkCycle = t % 5.7;
      const blink = blinkCycle > 4.85 && blinkCycle < 5.05 ? 0.38 : 0;
      rig.eyelids.forEach((bone, index) => {
        applyRotation(bone, index % 2 === 0 ? -blink : blink, 0, 0);
      });
    };

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
        const normalized = 3.2 / Math.max(size.x, size.y, size.z, 0.001);
        model.scale.setScalar(normalized);
        pantherRoot.add(model);

        // Attach the crown to the most likely head/skull bone when the rig exposes one.
        let headBone: THREE.Object3D | null = null;
        model.traverse((node) => {
          if (!headBone && /head|skull|neck/i.test(node.name) && node instanceof THREE.Bone) headBone = node;
        });
        if (headBone) {
          crown.position.set(0, 0.22, 0);
          headBone.add(crown);
        } else {
          crown.position.set(0, 1.72, 0);
        }
        crown.visible = true;

        const pantherRig = buildPantherRig(model);
        (model.userData as { pantherRig?: PantherRig }).pantherRig = pantherRig;

        if (gltf.animations.length) {
          mixer = new THREE.AnimationMixer(model);
          const idle = findClip(gltf.animations, [/idle/i, /stand/i, /rest/i]);
          const walk = findClip(gltf.animations, [/walk/i, /stalk/i, /prowl/i, /roam/i]);
          const run = findClip(gltf.animations, [/run/i, /sprint/i, /gallop/i]);
          const turnLeft = findClip(gltf.animations, [/left.*turn/i, /turn.*left/i]);
          const turnRight = findClip(gltf.animations, [/right.*turn/i, /turn.*right/i]);
          const sit = findClip(gltf.animations, [/sit/i, /sitting/i]);
          const stand = findClip(gltf.animations, [/stand/i, /stand[- ]?up/i]);
          const rest = findClip(gltf.animations, [/sleep/i, /rest/i, /lay/i]);
          const fallback = gltf.animations[0];
          playAction(idle ?? stand ?? walk ?? fallback, 0);
          (model.userData as {
            idle?: THREE.AnimationClip;
            walk?: THREE.AnimationClip;
            run?: THREE.AnimationClip;
            turnLeft?: THREE.AnimationClip;
            turnRight?: THREE.AnimationClip;
            sit?: THREE.AnimationClip;
            stand?: THREE.AnimationClip;
            rest?: THREE.AnimationClip;
          }).idle = idle ?? stand ?? fallback;
          (model.userData as {
            idle?: THREE.AnimationClip;
            walk?: THREE.AnimationClip;
            run?: THREE.AnimationClip;
            turnLeft?: THREE.AnimationClip;
            turnRight?: THREE.AnimationClip;
            sit?: THREE.AnimationClip;
            stand?: THREE.AnimationClip;
            rest?: THREE.AnimationClip;
          }).walk = walk ?? idle ?? fallback;
          (model.userData as { run?: THREE.AnimationClip }).run = run ?? walk ?? idle ?? fallback;
          (model.userData as { turnLeft?: THREE.AnimationClip; turnRight?: THREE.AnimationClip }).turnLeft = turnLeft ?? walk ?? idle ?? fallback;
          (model.userData as { turnLeft?: THREE.AnimationClip; turnRight?: THREE.AnimationClip }).turnRight = turnRight ?? walk ?? idle ?? fallback;
          (model.userData as { sit?: THREE.AnimationClip; stand?: THREE.AnimationClip; rest?: THREE.AnimationClip }).sit = sit ?? idle ?? fallback;
          (model.userData as { stand?: THREE.AnimationClip }).stand = stand ?? idle ?? fallback;
          (model.userData as { rest?: THREE.AnimationClip }).rest = rest ?? idle ?? fallback;
        }
      },
      undefined,
      () => {
        // Keep the slot empty if the licensed production GLB is not present.
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
    let wasMoving = false;

    const animate = () => {
      raf = requestAnimationFrame(animate);
      const dt = clock.getDelta();
      const t = clock.elapsedTime;

      starsFar.rotation.y = t * 0.0014;
      starsNear.rotation.y = -t * 0.0021;
      galaxy.rotation.y = t * 0.0032;
      solarSystem.rotation.y = t * 0.005;
      solarSystem.rotation.x = Math.sin(t * 0.08) * 0.035;
      orbitGroups.forEach((orbit) => { orbit.rotation.y += Number(orbit.userData.speed) * 0.002; orbit.children.forEach((child) => { const moonSpeed=Number((child as THREE.Object3D).userData.moonSpeed||0); if(moonSpeed) child.rotation.y += moonSpeed*0.004; }); });

      if (model) {
        const roamX = Math.sin(t * 0.085) * 2.8;
        const roamZ = Math.cos(t * 0.065) * 1.9;
        const targetX = 1.8 + roamX;
        const targetZ = 1.1 + roamZ;
        const moving = Math.abs(roamX) + Math.abs(roamZ) > 0.65;
        const behaviorTime = t % 32;
        const stalking = behaviorTime > 15 && behaviorTime < 21;
        const phase = behaviorTime < 5 ? "idle" : behaviorTime < 15 ? "walk" : behaviorTime < 21 ? "stalk" : behaviorTime < 27 ? "walk" : "idle";

        pantherRoot.position.x += (targetX - pantherRoot.position.x) * 0.012;
        pantherRoot.position.z += (targetZ - pantherRoot.position.z) * 0.012;
        pantherRoot.rotation.y = Math.atan2(
          roamX - Math.sin((t - 0.08) * 0.085) * 2.8,
          roamZ - Math.cos((t - 0.08) * 0.065) * 1.9,
        ) + pointer.x * 0.14;
        pantherRoot.position.y = -1.7 + Math.sin(t * (stalking ? 1.5 : 1.9)) * (stalking ? 0.009 : 0.018);

        const clips = model.userData as {
          idle?: THREE.AnimationClip;
          walk?: THREE.AnimationClip;
          run?: THREE.AnimationClip;
          turnLeft?: THREE.AnimationClip;
          turnRight?: THREE.AnimationClip;
          sit?: THREE.AnimationClip;
          stand?: THREE.AnimationClip;
          rest?: THREE.AnimationClip;
          pantherRig?: PantherRig;
        };
        const desiredClip =
          phase === "stalk" ? clips.walk :
          phase === "walk" ? clips.walk :
          clips.idle;

        if (moving !== wasMoving || (phase === "stalk" && wasMoving && !stalking)) {
          playAction(desiredClip);
          wasMoving = moving;
        }

        mixer?.update(dt);
        if (clips.pantherRig) {
          applyPantherBehavior(clips.pantherRig, t, moving, stalking);
        }
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
  const [error, setError] = useState("");\n  const [language, setLanguage] = useState<"fa" | "en">("fa");

  useEffect(() => {
    if (!user || profile) return;
    complete(user.displayName || "کاربر سلف", user.primaryEmail?.split("@")[0] || "salf1_user", "Pᴇʀsɪᴀɴ ᴮᵒᵗ · SELF");
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

  const fa = language === "fa";
  const copy = fa ? {
    gate:"درگاه هویت امن", intro:"هویت،", intro2:"پیش از ورود.", lede:"درگاه ورود به قلمرو خصوصی سلف؛ تجربه‌ای سه‌بعدی سینمایی با پلنگ سیاه، منظومه شمسی و کهکشان.", title:"ورود به قلمرو سلف", desc:"هویت خود را تأیید کنید تا ورود امن به محیط SALF1 آغاز شود.", auth:"احراز هویت", ready:"آماده", private:"دسترسی خصوصی", secure:"اطلاعات حساب فقط برای ایجاد یک ورود امن استفاده می‌شود.", connecting:"در حال اتصال…", verify:"تأیید و ورود امن با ", encrypted:"ارتباط رمزنگاری‌شده · انتقال امن", loading:"{copy.loading}", wait:"{copy.wait}"
  } : {
    gate:"SECURE IDENTITY GATE", intro:"IDENTITY", intro2:"BEFORE ENTRY.", lede:"Private access to the SALF1 realm — a cinematic 3D experience with a black panther, the Solar System and deep space.", title:"ENTER THE REALM", desc:"Verify your identity to begin secure access to SALF1.", auth:"AUTHENTICATION", ready:"READY", private:"PRIVATE ACCESS", secure:"Account data is used only to establish a secure session.", connecting:"Connecting…", verify:"Secure sign-in with ", encrypted:"Encrypted connection · Secure transfer", loading:"ENTERING THE REALM", wait:"Please wait a moment…"
  };

  if (isPending) {
    return <div className={"pb-auth pb-auth--space " + (fa ? "pb-auth--fa" : "pb-auth--en")} dir={fa ? "rtl" : "ltr"}><SolarRealm /><div className="pb-auth__space-vignette" /><div className="pb-auth__loading"><div className="pb-auth__loading-card"><div className="pb-seal pb-seal--loading" aria-hidden><span>P</span><i /><b /></div><p className="pb-auth__loading-kicker">Pᴇʀsɪᴀɴ ᴮᵒᵗ · PRIVATE</p><h1 className="pb-auth__loading-title">در حال ورود به قلمرو</h1><div className="pb-auth__progress" aria-hidden><span /></div><p className="pb-auth__loading-copy">لطفاً چند لحظه صبر کنید…</p></div></div></div>;
  }

  if (user && profile) {
    return <div className={"pb-auth pb-auth--space " + (fa ? "pb-auth--fa" : "pb-auth--en")} dir={fa ? "rtl" : "ltr"}><SolarRealm /><div className="pb-auth__space-vignette" /></div>;
  }

  return (
    <div className={"pb-auth pb-auth--space " + (fa ? "pb-auth--fa" : "pb-auth--en")} dir={fa ? "rtl" : "ltr"}>
      <SolarRealm />
      <div className="pb-auth__space-vignette" />
      <header className="pb-auth__top">
        <div className="pb-auth__brand"><div className="pb-auth__mini-seal" aria-hidden><span>P</span></div><div className="pb-auth__brand-copy"><strong>Pᴇʀsɪᴀɴ ᴮᵒᵗ</strong><small>SALF1 · PRIVATE MANAGEMENT REALM</small></div></div>
        <div className="pb-auth__secure"><i /><span>{copy.gate}</span></div><div className="pb-auth__language"><button className={fa ? "active" : ""} onClick={() => setLanguage("fa")}>فارسی</button><button className={!fa ? "active" : ""} onClick={() => setLanguage("en")}>ENGLISH</button></div>
      </header>
      <main className="pb-auth__body pb-auth__body--space">
        <section className="pb-auth__intro pb-auth__intro--space">
          <div className="pb-auth__intro-line"><span>01</span><i /><span>{copy.gate}</span></div>
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
                <span className="pb-auth__provider-copy"><strong>{busy === provider.providerId ? copy.connecting : copy.verify + provider.label}</strong><small>{copy.encrypted}</small></span>
                <ArrowUpLeft className="pb-auth__provider-arrow size-4" />
              </button>
            ))}
          </div>
          {error ? <div className="pb-auth__error" role="alert">{error}</div> : null}
          <div className="pb-auth__divider"><span>{copy.private}</span></div>
          <div className="pb-auth__footnote"><ShieldCheck className="size-3.5" /><span>{copy.secure}</span></div>
        </section>
      </main>
      <footer className="pb-auth__footer"><span>Pᴇʀsɪᴀɴ ᴮᵒᵗ</span><span>SALF1 · PANTHERA REALM</span><span>JAWATI · 2026</span></footer>
    </div>
  );
}
