import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "meshoptimizer";

import { HybridSceneViewer } from "./hybrid-viewer.js";
import { PAGE_DATA } from "./data.js";

const PAGE_CACHE_VERSION = "20260706_copy_polish";
const transientViewers = new WeakMap();
let playgroundHintTimer = 0;

class MeshSceneViewer {
  constructor(container) {
    this.container = container;
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.controls = null;
    this.root = null;
    this.resizeObserver = null;
    this.animationId = 0;
    this.disposed = false;
  }

  async load(url) {
    this.dispose();
    this.disposed = false;
    this.container.classList.add("mesh-viewer");
    this.container.innerHTML = '<div class="viewer-loading">Loading mesh...</div>';

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xe6ebef);
    this.camera = new THREE.PerspectiveCamera(44, 1, 0.01, 200);
    this.camera.up.set(0, 0, 1);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.08;
    this.container.innerHTML = "";
    this.container.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x7b8490, 2.0));
    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(2.5, -3.0, 4.0);
    this.scene.add(sun);

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(this.container);
    this.resize();

    try {
      const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
      const gltf = await loader.loadAsync(url);
      if (this.disposed) {
        disposeObject3D(gltf.scene);
        return;
      }
      this.root = gltf.scene;
      makeMatte(this.root);
      this.scene.add(this.root);
      this.fitCamera(this.root);
      this.animate();
    } catch (error) {
      this.container.innerHTML = `<div class="viewer-loading">Mesh failed to load: ${shortError(error)}</div>`;
    }
  }

  fitCamera(root) {
    const box = new THREE.Box3().setFromObject(root);
    if (box.isEmpty()) {
      this.camera.position.set(1.4, -1.8, 1.2);
      this.controls.target.set(0, 0, 0);
      return;
    }

    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const radius = Math.max(size.x, size.y, size.z, 0.2) * 0.5;
    const distance = radius / Math.sin(THREE.MathUtils.degToRad(this.camera.fov * 0.5));
    this.controls.target.copy(center);
    this.camera.position.copy(center).add(new THREE.Vector3(distance * 0.9, -distance * 1.25, distance * 0.75));
    this.camera.near = Math.max(distance / 200, 0.001);
    this.camera.far = Math.max(distance * 20, 10);
    this.camera.updateProjectionMatrix();
    this.controls.update();
  }

  resize() {
    if (!this.renderer || !this.camera) return;
    const width = Math.max(1, this.container.clientWidth);
    const height = Math.max(1, this.container.clientHeight);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  animate() {
    if (this.disposed) return;
    this.controls?.update();
    this.renderer?.render(this.scene, this.camera);
    this.animationId = requestAnimationFrame(() => this.animate());
  }

  dispose() {
    this.disposed = true;
    if (this.animationId) cancelAnimationFrame(this.animationId);
    this.animationId = 0;
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    if (this.root) {
      disposeObject3D(this.root);
      this.root = null;
    }
    this.controls?.dispose?.();
    this.controls = null;
    this.renderer?.dispose?.();
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.container.innerHTML = "";
  }
}

function disposeViewer(container) {
  const previous = transientViewers.get(container);
  previous?.dispose?.();
  transientViewers.delete(container);
}

function loadHybrid(container, manifest) {
  disposeViewer(container);
  const viewer = new HybridSceneViewer(container);
  transientViewers.set(container, viewer);
  viewer.load(manifest);
}

function loadMesh(container, url) {
  disposeViewer(container);
  const viewer = new MeshSceneViewer(container);
  transientViewers.set(container, viewer);
  viewer.load(url);
}

function disposeObject3D(root) {
  root.traverse((object) => {
    if (!object.isMesh) return;
    object.geometry?.dispose?.();
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    materials.forEach((material) => material?.dispose?.());
  });
}

function makeMatte(root) {
  root.traverse((object) => {
    if (!object.isMesh || !object.material) return;
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    materials.forEach((material) => {
      if ("metalness" in material) material.metalness = 0;
      if ("roughness" in material) material.roughness = 1;
      material.needsUpdate = true;
    });
  });
}

function shortError(error) {
  return String(error?.message || error || "unknown").slice(0, 120);
}

function buildTabs(container, cases, onSelect) {
  container.innerHTML = "";
  cases.forEach((item, index) => {
    const button = document.createElement("button");
    button.className = "tab-button";
    button.type = "button";
    button.role = "tab";
    button.textContent = item.title;
    button.addEventListener("click", () => {
      [...container.children].forEach((child) => {
        child.classList.toggle("is-active", child === button);
        child.setAttribute("aria-selected", child === button ? "true" : "false");
      });
      onSelect(item, index);
    });
    container.appendChild(button);
  });
}

function selectTab(container, index = 0) {
  const button = container.children[index];
  if (button) button.click();
}

function populateMainViewerScenes() {
  const select = document.getElementById("scene-select");
  select.innerHTML = "";
  for (const item of PAGE_DATA.showcase) {
    const option = document.createElement("option");
    option.value = item.manifest;
    option.dataset.gsScene = item.gsScene;
    option.textContent = `${item.title} - ${item.sessionId}`;
    select.appendChild(option);
  }
}

function initShowcaseTabs() {
  const tabs = document.getElementById("showcase-tabs");
  const select = document.getElementById("scene-select");
  const app = window.RapierRigidBodyDemo.app;
  populateMainViewerScenes();

  buildTabs(tabs, PAGE_DATA.showcase, async (item) => {
    updatePlaygroundInputOverlay(item);
    select.value = item.manifest;
    app.syncGsSceneFromSelection();
    await app.loadGeneratedSceneFromInput();
    showPlaygroundClickHints();
  });
  selectTab(tabs, 0);
}

function updatePlaygroundInputOverlay(item) {
  const inputOverlay = document.getElementById("playground-input-overlay");
  if (!inputOverlay) return;

  if (!item?.input) {
    inputOverlay.hidden = true;
    inputOverlay.removeAttribute("src");
    inputOverlay.removeAttribute("data-fallback-src");
    return;
  }

  inputOverlay.alt = `${item.title} input image`;
  inputOverlay.hidden = true;
  inputOverlay.onload = () => {
    inputOverlay.hidden = false;
  };
  inputOverlay.onerror = () => {
    const fallbackSrc = inputOverlay.dataset.fallbackSrc;
    if (fallbackSrc && inputOverlay.src !== fallbackSrc) {
      inputOverlay.removeAttribute("data-fallback-src");
      inputOverlay.src = fallbackSrc;
      return;
    }
    inputOverlay.hidden = true;
  };

  const primarySrc = cacheBustPageAssetUrl(item.input, new URL("./", window.location.href));
  const fallbackSrc = cacheBustPageAssetUrl(item.input, `${window.location.origin}/`);
  if (primarySrc !== fallbackSrc) {
    inputOverlay.dataset.fallbackSrc = fallbackSrc;
  } else {
    inputOverlay.removeAttribute("data-fallback-src");
  }
  inputOverlay.src = primarySrc;
}

function cacheBustPageAssetUrl(path, baseUrl) {
  const url = new URL(String(path ?? "").replace(/^\/+/, ""), baseUrl);
  url.searchParams.set("v", PAGE_CACHE_VERSION);
  return url.href;
}

function showPlaygroundClickHints() {
  const root = document.getElementById("sim-root");
  const layer = document.getElementById("playground-hint-layer");
  if (!root || !layer) return;

  clearPlaygroundClickHints();
  const rootRect = root.getBoundingClientRect();
  const points = [
    { x: rootRect.width * 0.5, y: rootRect.height * 0.52, center: true },
    ...["physics-button", "load-robot-button", "load-character-button"]
      .map((id) => pointForElement(document.getElementById(id), rootRect))
      .filter(Boolean),
  ];

  for (const point of points) {
    const hint = document.createElement("div");
    hint.className = `click-hint${point.center ? " click-hint-center" : ""}`;
    hint.style.left = `${point.x}px`;
    hint.style.top = `${point.y}px`;
    hint.innerHTML = `
      <div class="mouse-icon"><span class="mouse-button"></span></div>
      <span class="click-ring"></span>
    `;
    layer.appendChild(hint);
  }

  playgroundHintTimer = window.setTimeout(clearPlaygroundClickHints, 6000);
}

function pointForElement(element, rootRect) {
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return null;
  return {
    x: rect.left - rootRect.left + rect.width * 0.5,
    y: rect.top - rootRect.top + rect.height * 0.5,
  };
}

function clearPlaygroundClickHints() {
  if (playgroundHintTimer) {
    window.clearTimeout(playgroundHintTimer);
    playgroundHintTimer = 0;
  }
  document.getElementById("playground-hint-layer")?.replaceChildren();
}

function initSimfoundryComparison() {
  const tabs = document.getElementById("simfoundry-tabs");
  const input = document.getElementById("simfoundry-input");
  const oursContainer = document.getElementById("simfoundry-ours");
  const outputViewer = document.getElementById("simfoundry-output-viewer");
  const outputVideo = document.getElementById("simfoundry-output-video");

  const oursViewer = new window.RapierRigidBodyDemo.SceneOnlyViewer(oursContainer);

  buildTabs(tabs, PAGE_DATA.simfoundryCompare, async (item) => {
    input.src = item.input;

    oursViewer.loadScene(item.ours.manifest, item.ours.gsScene);
    clearVideo(outputVideo);

    if (item.mode === "hybrid") {
      outputVideo.classList.add("is-hidden");
      outputViewer.classList.remove("is-hidden");
      loadHybrid(outputViewer, item.simfoundry.manifest);
      return;
    }

    if (item.mode === "mesh") {
      outputVideo.classList.add("is-hidden");
      outputViewer.classList.remove("is-hidden");
      loadMesh(outputViewer, item.simfoundryMesh);
      return;
    }

    disposeViewer(outputViewer);
    outputViewer.classList.add("is-hidden");
    outputVideo.classList.remove("is-hidden");
    outputVideo.src = item.simfoundryVideo;
    outputVideo.load();
  });
  selectWhenVisible(document.getElementById("comparisons"), () => selectTab(tabs, 0));
}

function initReconstructedScenes() {
  const tabs = document.getElementById("reconstructed-tabs");
  const viewerContainer = document.getElementById("reconstructed-viewer");
  const inputOverlay = document.getElementById("reconstructed-input-overlay");
  if (!tabs || !viewerContainer || !inputOverlay) return;

  const viewer = new window.RapierRigidBodyDemo.SceneOnlyViewer(viewerContainer);

  buildTabs(tabs, PAGE_DATA.reconstructedScenes, async (item) => {
    inputOverlay.src = item.input;
    inputOverlay.alt = `${item.title} input image`;
    viewer.loadScene(item.manifest, item.gsScene);
  });
  selectWhenVisible(document.getElementById("reconstructed"), () => selectTab(tabs, 0));
}

function clearVideo(video) {
  video.pause();
  video.removeAttribute("src");
  video.load();
}

function selectWhenVisible(element, callback) {
  let done = false;
  const run = () => {
    if (done) return;
    done = true;
    callback();
  };
  if (!("IntersectionObserver" in window)) {
    run();
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      observer.disconnect();
      run();
    }
  }, { rootMargin: "220px 0px" });
  observer.observe(element);
}

function waitForProjectViewer() {
  return new Promise((resolve) => {
    const check = () => {
      if (window.RapierRigidBodyDemo?.app && window.RapierRigidBodyDemo?.SceneOnlyViewer) {
        resolve();
      } else {
        requestAnimationFrame(check);
      }
    };
    check();
  });
}

await waitForProjectViewer();
initShowcaseTabs();
initSimfoundryComparison();
initReconstructedScenes();
