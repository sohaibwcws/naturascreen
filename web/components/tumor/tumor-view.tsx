"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { SimFrame } from "@/lib/types";

const MAX_CELLS = 6000;
// Cell-state colours — must match tailwind.config `cell.*` and the legend.
const STATE_COLORS = [
  new THREE.Color("#46d98a"), // 0 dividing
  new THREE.Color("#f2b134"), // 1 stressed
  new THREE.Color("#f2603c"), // 2 dying
];
const DOMAIN_RADIUS = 42;

function Cells({ frame }: { frame: SimFrame | null }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const dummy = useRef(new THREE.Object3D());

  useEffect(() => {
    const mesh = ref.current;
    if (!mesh || !frame) return;
    const n = Math.min(frame.states.length, MAX_CELLS);
    for (let i = 0; i < n; i++) {
      dummy.current.position.set(
        frame.positions[i * 3],
        frame.positions[i * 3 + 1],
        frame.positions[i * 3 + 2],
      );
      dummy.current.updateMatrix();
      mesh.setMatrixAt(i, dummy.current.matrix);
      mesh.setColorAt(i, STATE_COLORS[frame.states[i]] ?? STATE_COLORS[0]);
    }
    mesh.count = n;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [frame]);

  return (
    <instancedMesh ref={ref} args={[undefined, undefined, MAX_CELLS]} frustumCulled={false}>
      <sphereGeometry args={[1.15, 10, 10]} />
      <meshStandardMaterial roughness={0.45} metalness={0.05} toneMapped={false} />
    </instancedMesh>
  );
}

function Scene({ frame }: { frame: SimFrame | null }) {
  return (
    <>
      <ambientLight intensity={0.7} />
      <directionalLight position={[40, 60, 40]} intensity={1.1} />
      <directionalLight position={[-40, -20, -30]} intensity={0.3} color="#3fd0c9" />
      <mesh>
        <sphereGeometry args={[DOMAIN_RADIUS, 24, 24]} />
        <meshBasicMaterial color="#1c2430" wireframe transparent opacity={0.18} />
      </mesh>
      <Cells frame={frame} />
      <OrbitControls enablePan={false} minDistance={60} maxDistance={260} autoRotate autoRotateSpeed={0.4} />
    </>
  );
}

/**
 * The live tumor view. HARD-GATED on the simulation notice (spec §3): if no notice has
 * arrived, no cells are drawn — only a placeholder. When present, the notice is overlaid
 * persistently on the canvas, as load-bearing as the cure disclaimer.
 */
export function TumorView({ frame, notice }: { frame: SimFrame | null; notice: string | null }) {
  if (!notice) {
    return (
      <div className="panel grid h-[420px] place-items-center text-center text-sm text-ink-faint">
        Waiting for the simulation safety notice. No cells are rendered until it is shown.
      </div>
    );
  }
  return (
    <div className="panel relative h-[420px] overflow-hidden">
      <Canvas camera={{ position: [0, 0, 150], fov: 45 }} dpr={[1, 2]}>
        <color attach="background" args={["#0c1118"]} />
        <Scene frame={frame} />
      </Canvas>
      <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-base-900/95 to-transparent p-3">
        <p className="flex items-start gap-2 text-[11px] leading-snug text-warn/90">
          <span className="mt-px font-semibold uppercase tracking-wide">Illustrative</span>
          <span className="text-ink-muted">{notice}</span>
        </p>
      </div>
    </div>
  );
}
