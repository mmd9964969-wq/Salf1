# SALF1 Panther Animation Profile

This is the runtime behavior target for the realistic black-panther presentation.

## Behavioral cycle

1. **Idle / Alert** — calm standing, chest breathing, small weight shifts.
2. **Walk / Roam** — slow quadruped gait with alternating limb phase.
3. **Stalk** — lowered body, shorter stride, reduced vertical motion.
4. **Head Scan** — subtle horizontal/vertical head movement rather than robotic snapping.
5. **Ear Attention** — independent small ear rotations.
6. **Tail Balance** — low-frequency tail movement coupled to locomotion.
7. **Blink** — irregular natural blink timing.
8. **Jaw Micro-motion** — tiny non-verbal facial movement.
9. **Turn** — body yaw follows the roaming trajectory.
10. **Rest / Settle** — optional idle/rest clips when supplied by the licensed model.
11. **Run / Burst** — recognized automatically when a free/licensed runtime clip exists.

## Runtime rule

The animation layer is intentionally additive. It can operate with:
- a separately licensed/free GLB that contains clips, or
- only a compatible rig, in which case the procedural secondary-motion layer remains active.

No Fab animation data is bundled or reconstructed from the commercial package.

## Visual target

The Fab Black Javan Leopard gallery remains a **visual reference only**:
https://www.fab.com/listings/003ba7b1-e6f6-4bc9-9f9f-740fa1e54689
