#!/usr/bin/env python3
"""Prepare standalone assets for the comparison project page."""

from __future__ import annotations

import json
import re
import shutil
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PAGE = ROOT / "web_preview" / "web_page"
ASSETS = PAGE / "assets"
DATA_JS = PAGE / "src" / "data.js"
JSON_CHUNK_TYPE = 0x4E4F534A
ASSET_PATH_RE = re.compile(r"(?:/[A-Za-z0-9_.-]+)+/users/[A-Za-z0-9_.-]+/|/(?:home|root|Users)/")
SENSITIVE_METADATA_KEY_RE = re.compile(
    r"(command|stdout|stderr|traceback|conda|checkpoint|train_out_dir|export_dir|output_dir|"
    r"input_blend|final_blend|gravity_.*blend|pipeline_.*|sam3d_.*blend|raw|compress|gltfpack)",
    re.IGNORECASE,
)
ALLOWED_GLTF_EXTRAS = {"mask_id", "semantic_label", "final_3d_object_name"}


OUR_SCENES = {
    "ai_image": ("AI Image", "20260704_113332_03959801"),
    "bathroom": ("Bathroom", "20260703_231333_72ed5ffc"),
    "clutter_table": ("Clutter Table", "20260704_115926_205c8236"),
    "cluttered_scene_1": ("Cluttered Scene 1", "20260704_121638_4b1f69d1"),
    "coffee": ("Coffee", "20260704_123755_257c3780"),
    "dining": ("Dining", "20260704_124715_f1f26271"),
    "fruits": ("Fruits", "20260704_143037_c5a9e69c"),
    "home_coffee": ("Home Coffee", "20260705_160515_84b50dd9"),
    "kitchen1": ("Kitchen", "20260704_154018_4c37fbda"),
    "kitchen2": ("Kitchen 2", "20260704_155258_c607afba"),
    "living": ("Living", "20260704_184725_c2acdd53"),
    "opensource_ocid": ("Open Source OCID", "20260704_165033_187e900b"),
    "outdoor": ("Outdoor", "20260704_181443_2ec44630"),
    "toys": ("Toys", "20260704_171553_9a43fa25"),
}

RECONSTRUCTED_SCENES = {
    "food_plate": ("food_plate", "20260704_205848_2f0dac13"),
    "food_table": ("food_table", "20260705_130731_c56910e6"),
    "kitchen_fysics": ("kitchen_fysics", "20260705_225155_bc2e0803"),
    "office_fysics": ("office_fysics", "20260705_232557_e2b5a61f"),
}

HYBRID_COMPARE = [
    ("cluttered_scene_1", "Cluttered Scene 1", "desk", "Desk"),
    ("kitchen1", "Kitchen", "kitchen", "Kitchen"),
    ("dining", "Dining", "dining", "Dining"),
    ("toys", "Toys", "toys", "Toys"),
    ("outdoor", "Outdoor", "outdoor", "Outdoor"),
]

SIMFOUNDRY_HYBRID_DIRS = {
    "desk": ROOT / "simfoundry_assets/cases/02_simfoundry_reconstructed_scenes/01_desk",
    "kitchen": ROOT / "simfoundry_assets/cases/02_simfoundry_reconstructed_scenes/02_kitchen",
    "dining": ROOT / "simfoundry_assets/cases/02_simfoundry_reconstructed_scenes/03_dining",
    "toys": ROOT / "simfoundry_assets/cases/02_simfoundry_reconstructed_scenes/04_toys",
    "outdoor": ROOT / "simfoundry_assets/cases/02_simfoundry_reconstructed_scenes/05_outdoor",
}

DIGITAL_VIDEO_CASES = [
    ("bathroom", "Bathroom", ROOT / "simfoundry_assets/cases/06_digital_twin_and_cousin_generation/01_bathroom/raw/002_reconstructed_twins__bathroom_1_demo_plus_20.mp4"),
    ("coffee", "Coffee", ROOT / "simfoundry_assets/cases/06_digital_twin_and_cousin_generation/02_coffee/raw/002_reconstructed_twins__coffee_2_demo_plus_30.mp4"),
    ("fruits", "Fruits", ROOT / "simfoundry_assets/cases/06_digital_twin_and_cousin_generation/04_fruits/raw/002_reconstructed_twins__fruits_2_demo_plus_20.mp4"),
    ("home_coffee", "Home Coffee", ROOT / "simfoundry_assets/cases/06_digital_twin_and_cousin_generation/05_home_coffee/raw/002_reconstructed_twins__home_coffee_4_plus_20.mp4"),
    ("living", "Living", ROOT / "simfoundry_assets/cases/06_digital_twin_and_cousin_generation/07_living/raw/002_reconstructed_twins__living_3_demo_plus_10.mp4"),
]

SAM3D_CASES = [
    ("ai_image", "AI Image", ROOT / "simfoundry_assets/cases/10_reconstructed_scene_vs_sam3d/04_ai_image"),
    ("opensource_ocid", "Open Source OCID", ROOT / "simfoundry_assets/cases/10_reconstructed_scene_vs_sam3d/01_open_source_ocid"),
]


def rel(path: Path) -> str:
    return path.relative_to(PAGE).as_posix()


def copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size == src.stat().st_size:
        return
    shutil.copy2(src, dst)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def public_path(value: str) -> str:
    normalized = str(value).replace("\\", "/")
    sessions_index = normalized.find("/sessions/")
    if sessions_index >= 0:
        return normalized[sessions_index + 1:]
    page_index = normalized.find("/web_preview/web_page/")
    if page_index >= 0:
        return normalized[page_index + len("/web_preview/web_page/"):]
    project_assets_index = normalized.find("/project_page/assets/")
    if project_assets_index >= 0:
        return "assets/" + normalized[project_assets_index + len("/project_page/assets/"):]
    return "" if ASSET_PATH_RE.search(normalized) else str(value)


def strip_private_metadata(value, key: str = ""):
    if isinstance(value, dict):
        if key == "extras":
            return {
                item_key: strip_private_metadata(item_value, item_key)
                for item_key, item_value in value.items()
                if item_key in ALLOWED_GLTF_EXTRAS
            }

        cleaned = {}
        for item_key, item_value in value.items():
            lowered = str(item_key).lower()
            if SENSITIVE_METADATA_KEY_RE.search(lowered):
                continue
            if item_key in {"source", "source_path", "simplified_source_path", "manifest_path", "camera_json", "local_path", "local_url"}:
                continue
            cleaned_value = strip_private_metadata(item_value, item_key)
            if cleaned_value == "" and isinstance(item_value, str) and ASSET_PATH_RE.search(item_value):
                continue
            cleaned[item_key] = cleaned_value
        return cleaned

    if isinstance(value, list):
        return [strip_private_metadata(item, key) for item in value]

    if isinstance(value, str):
        return public_path(value)

    return value


def mask_id_from_name(name: str) -> int | None:
    match = re.search(r"mask_(\d+)", name or "")
    return int(match.group(1)) if match else None


def copy_tree_files(src_dir: Path, dst_dir: Path, pattern: str = "*") -> None:
    if not src_dir.exists():
        return
    for src in src_dir.rglob(pattern):
        if src.is_file():
            copy_file(src, dst_dir / src.relative_to(src_dir))


def sanitize_final_scene_manifest(manifest: dict) -> dict:
    cleaned = {}
    if manifest.get("schema"):
        cleaned["schema"] = manifest["schema"]
    for key in ("ground_z", "support", "physics", "sapien"):
        if key in manifest:
            cleaned[key] = strip_private_metadata(manifest[key])

    objects = []
    for raw_obj in manifest.get("objects", []):
        sapien_export = raw_obj.get("sapien_export") if isinstance(raw_obj.get("sapien_export"), dict) else raw_obj
        obj = {}
        for key in ("index", "mask_id", "final_3d_object_name", "semantic_label", "description"):
            if key in raw_obj:
                obj[key] = raw_obj[key]
        for key in ("web_asset_glb", "web_glb", "web_visual_path"):
            if raw_obj.get(key):
                obj[key] = public_path(raw_obj[key])
        if isinstance(raw_obj.get("web_asset"), dict):
            web_asset = {}
            for key in ("glb", "web_glb", "web_asset_glb"):
                if raw_obj["web_asset"].get(key):
                    web_asset[key] = public_path(raw_obj["web_asset"][key])
            if web_asset:
                obj["web_asset"] = web_asset
        if isinstance(raw_obj.get("sapien_final_pose"), dict) and raw_obj["sapien_final_pose"].get("final_pose") is not None:
            obj["sapien_final_pose"] = {"final_pose": raw_obj["sapien_final_pose"]["final_pose"]}

        sapien = {}
        for key in ("name", "initial_pose", "bbox_min", "bbox_max"):
            if key in sapien_export:
                sapien[key] = sapien_export[key]
        collision_paths = [
            public_path(path)
            for path in sapien_export.get("collision_paths", [])
            if str(path).endswith(".obj")
        ]
        sapien["collision_path"] = ""
        sapien["collision_paths"] = collision_paths
        sapien["collision_part_count"] = len(collision_paths)
        obj["sapien_export"] = sapien
        objects.append(obj)

    cleaned["objects"] = objects
    return cleaned


def sanitize_3dgs_scene_manifest(manifest: dict) -> dict:
    cleaned = {}
    for key in (
        "schema",
        "world_up",
        "coordinate_system",
        "splat",
        "camera",
        "alignment",
        "world_transform",
    ):
        if key in manifest:
            cleaned[key] = strip_private_metadata(manifest[key])
    return cleaned


def sanitize_display_scene_manifest(manifest: dict) -> dict:
    cleaned = sanitize_final_scene_manifest(manifest)
    for raw_obj in cleaned.get("objects", []):
        sapien_export = raw_obj.get("sapien_export", {})
        sapien_export["collision_path"] = ""
        sapien_export["collision_paths"] = []
        sapien_export["collision_part_count"] = 0
    return cleaned


def sanitize_web_assets_manifest(manifest: dict) -> dict:
    cleaned = {}
    if manifest.get("schema"):
        cleaned["schema"] = manifest["schema"]
    if manifest.get("visual_frame") or manifest.get("visualFrame"):
        cleaned["visual_frame"] = manifest.get("visual_frame") or manifest.get("visualFrame")
    cleaned["objects"] = []
    for raw_obj in manifest.get("objects", []):
        obj = {}
        for key in ("index", "mask_id", "name", "final_3d_object_name", "label", "semantic_label"):
            if key in raw_obj:
                obj[key] = raw_obj[key]
        web_glb = raw_obj.get("web_glb") or raw_obj.get("web_asset_glb") or raw_obj.get("visual_path")
        if web_glb:
            obj["web_glb"] = public_path(web_glb)
        cleaned["objects"].append(obj)
    return cleaned


def sanitize_3dgs_manifest(manifest: dict) -> dict:
    cleaned = {}
    if manifest.get("schema"):
        cleaned["schema"] = manifest["schema"]
    if manifest.get("status"):
        cleaned["status"] = manifest["status"]
    cleaned["ksplat"] = "background.ksplat"
    cleaned["scene_json"] = "scene.json"
    if manifest.get("camera"):
        cleaned["camera"] = strip_private_metadata(manifest["camera"])
    return cleaned


def page_path_for_session_asset(path: str) -> Path:
    normalized = str(path).replace("\\", "/")
    marker = "/sessions/"
    marker_index = normalized.find(marker)
    if marker_index >= 0:
        return PAGE / normalized[marker_index + 1:]
    source_path = Path(path)
    if source_path.is_absolute():
        return PAGE / source_path.relative_to(ROOT)
    return PAGE / source_path


def copy_collision_parts(manifest: dict) -> int:
    copied = 0
    for raw_obj in manifest.get("objects", []):
        sapien_export = raw_obj.get("sapien_export")
        if not isinstance(sapien_export, dict):
            continue
        for raw_path in sapien_export.get("collision_paths", []):
            src = Path(raw_path)
            if not src.exists():
                continue
            copy_file(src, page_path_for_session_asset(raw_path))
            copied += 1
    return copied


def prepare_our_scene(key: str, title: str, session_id: str) -> dict:
    src = ROOT / "sessions" / session_id
    results = src / "results"
    dest = PAGE / "sessions" / session_id
    final_manifest = load_json(results / "final_scene_manifest.json")

    copy_file(src / "input/image.png", dest / "input" / "image.png")
    write_json(dest / "results" / "3dgs_bg" / "scene.json", sanitize_3dgs_scene_manifest(load_json(results / "3dgs_bg" / "scene.json")))
    write_json(dest / "results" / "3dgs_bg" / "manifest.json", sanitize_3dgs_manifest(load_json(results / "3dgs_bg" / "manifest.json")))
    copy_file(results / "3dgs_bg" / "background.ksplat", dest / "results" / "3dgs_bg" / "background.ksplat")
    write_json(dest / "results" / "web_assets" / "manifest.json", sanitize_web_assets_manifest(load_json(results / "web_assets" / "manifest.json")))
    copy_tree_files(results / "web_assets" / "web_objects", dest / "results" / "web_assets" / "web_objects", "*.glb")
    copied_collision_parts = copy_collision_parts(final_manifest)
    write_json(dest / "results" / "final_scene_manifest.json", sanitize_final_scene_manifest(final_manifest))

    return {
        "key": key,
        "title": title,
        "sessionId": session_id,
        "manifest": rel(dest / "results" / "final_scene_manifest.json"),
        "gsScene": rel(dest / "results" / "3dgs_bg" / "scene.json"),
        "input": rel(dest / "input" / "image.png"),
        "objectCount": len(final_manifest.get("objects", [])),
        "sourceObjectCount": len(final_manifest.get("objects", [])),
        "collisionPartCount": copied_collision_parts,
    }


def prepare_display_scene(key: str, title: str, session_id: str) -> dict:
    src = ROOT / "sessions" / session_id
    results = src / "results"
    dest = PAGE / "sessions" / session_id
    final_manifest = load_json(results / "final_scene_manifest.json")

    copy_file(src / "input/image.png", dest / "input" / "image.png")
    write_json(dest / "results" / "3dgs_bg" / "scene.json", sanitize_3dgs_scene_manifest(load_json(results / "3dgs_bg" / "scene.json")))
    write_json(dest / "results" / "3dgs_bg" / "manifest.json", sanitize_3dgs_manifest(load_json(results / "3dgs_bg" / "manifest.json")))
    copy_file(results / "3dgs_bg" / "background.ksplat", dest / "results" / "3dgs_bg" / "background.ksplat")
    write_json(dest / "results" / "web_assets" / "manifest.json", sanitize_web_assets_manifest(load_json(results / "web_assets" / "manifest.json")))
    copy_tree_files(results / "web_assets" / "web_objects", dest / "results" / "web_assets" / "web_objects", "*.glb")
    write_json(dest / "results" / "final_scene_manifest.json", sanitize_display_scene_manifest(final_manifest))

    return {
        "key": key,
        "title": title,
        "sessionId": session_id,
        "manifest": rel(dest / "results" / "final_scene_manifest.json"),
        "gsScene": rel(dest / "results" / "3dgs_bg" / "scene.json"),
        "input": rel(dest / "input" / "image.png"),
        "objectCount": len(final_manifest.get("objects", [])),
        "sourceObjectCount": len(final_manifest.get("objects", [])),
        "collisionPartCount": 0,
    }


def prepare_simfoundry_hybrid(key: str, source_dir: Path) -> dict:
    dest = ASSETS / "simfoundry" / "hybrid" / key
    metadata = load_json(source_dir / "metadata.json")
    scene_asset = next(a for a in metadata["assets"] if a["kind"] == "scene_manifest")
    scene = load_json(ROOT / scene_asset["local_path"])

    splat_assets = [a for a in metadata["assets"] if a["kind"] == "splat"]
    splat_asset = next((a for a in splat_assets if "local_url" in a["title"]), splat_assets[0])
    copy_file(ROOT / splat_asset["local_path"], dest / "background.ksplat")
    scene["splat"]["url"] = "background.ksplat"
    scene["splat"].pop("local_url", None)

    mesh_assets = {
        a.get("metadata", {}).get("name"): a
        for a in metadata["assets"]
        if a["kind"] == "mesh"
    }
    for obj in scene.get("objects", []):
        asset = mesh_assets.get(obj.get("name"))
        if not asset:
            continue
        source_path = ROOT / asset["local_path"]
        target_name = source_path.name
        copy_file(source_path, dest / "objects" / target_name)
        obj["url"] = f"objects/{target_name}"

    scene = strip_private_metadata(scene)
    scene.pop("preview_video", None)
    write_json(dest / "scene.json", scene)
    write_json(dest / "manifest.json", scene)
    return {
        "key": key,
        "title": metadata["title"],
        "manifest": rel(dest / "scene.json"),
        "objectCount": len(scene.get("objects", [])),
    }


def prepare_video(key: str, source: Path) -> str:
    dest = ASSETS / "simfoundry" / "videos" / f"{key}.mp4"
    copy_file(source, dest)
    return rel(dest)


def prepare_sam3d(key: str, source_dir: Path) -> dict:
    dest = ASSETS / "simfoundry" / "sam3d" / key
    raw = source_dir / "raw"
    copy_file(raw / "001_input_image.png", dest / "input.png")
    copy_file(raw / "002_simfoundry_output.glb", dest / "simfoundry_output.glb")
    return {
        "input": rel(dest / "input.png"),
        "mesh": rel(dest / "simfoundry_output.glb"),
    }


def prepare_project_page_assets() -> None:
    copy_tree_files(ROOT / "project_page" / "assets" / "character", ASSETS / "character")
    copy_tree_files(ROOT / "project_page" / "assets" / "urdf", ASSETS / "urdf")


def patch_glb_metadata(path: Path) -> bool:
    data = bytearray(path.read_bytes())
    if len(data) < 20 or data[:4] != b"glTF":
        return False
    chunk_len, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != JSON_CHUNK_TYPE:
        return False

    start = 20
    end = start + chunk_len
    try:
        document = json.loads(bytes(data[start:end]).rstrip(b" \t\r\n\x00").decode("utf-8"))
    except Exception:
        return False

    cleaned = strip_private_metadata(document)
    encoded = json.dumps(cleaned, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > chunk_len:
        return False
    data[start:end] = encoded + b" " * (chunk_len - len(encoded))
    path.write_bytes(data)
    return True


def patch_fbx_metadata(path: Path) -> int:
    data = bytearray(path.read_bytes())
    count = 0
    pattern = re.compile(rb"/[^\x00\s]*mixamo-mini/tmp/skins_[A-Za-z0-9\-]+\.fbx")
    for match in list(pattern.finditer(bytes(data))):
        replacement = b"mixamo_generated_animation.fbx"
        replacement = replacement + b" " * (match.end() - match.start() - len(replacement))
        data[match.start():match.end()] = replacement
        count += 1
    if count:
        path.write_bytes(data)
    return count


def sanitize_publish_assets() -> None:
    for path in (ASSETS / "urdf").glob("franka/franka_description/meshes/collision_coacd/*/manifest.json"):
        manifest = load_json(path)
        manifest.pop("source", None)
        write_json(path, manifest)

    for path in PAGE.rglob("*.glb"):
        patch_glb_metadata(path)
    for path in PAGE.rglob("*.fbx"):
        patch_fbx_metadata(path)


def main() -> None:
    (PAGE / "src").mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PAGE / "sessions", ignore_errors=True)
    shutil.rmtree(ASSETS / "ours", ignore_errors=True)
    prepare_project_page_assets()
    our = {
        key: prepare_our_scene(key, title, session_id)
        for key, (title, session_id) in OUR_SCENES.items()
    }
    reconstructed = {
        key: ({**our[key], "title": title, "collisionPartCount": 0}
              if key in our else prepare_display_scene(key, title, session_id))
        for key, (title, session_id) in RECONSTRUCTED_SCENES.items()
    }
    sim_hybrid = {
        key: prepare_simfoundry_hybrid(key, source_dir)
        for key, source_dir in SIMFOUNDRY_HYBRID_DIRS.items()
    }
    sim_videos = {
        key: prepare_video(key, source)
        for key, _, source in DIGITAL_VIDEO_CASES
    }
    sim_sam3d = {
        key: prepare_sam3d(key, source_dir)
        for key, _, source_dir in SAM3D_CASES
    }

    data = {
        "showcase": [our[key] for key in OUR_SCENES],
        "reconstructedScenes": [reconstructed[key] for key in RECONSTRUCTED_SCENES],
        "hybridCompare": [
            {
                "key": our_key,
                "title": title,
                "input": our[our_key]["input"],
                "ours": our[our_key],
                "simfoundry": sim_hybrid[sim_key],
                "simfoundryTitle": sim_title,
            }
            for our_key, title, sim_key, sim_title in HYBRID_COMPARE
        ],
        "digitalCompare": [
            {
                "key": key,
                "title": title,
                "input": our[key]["input"],
                "ours": our[key],
                "simfoundryVideo": sim_videos[key],
            }
            for key, title, _ in DIGITAL_VIDEO_CASES
        ],
        "sam3dCompare": [
            {
                "key": key,
                "title": title,
                "input": sim_sam3d[key]["input"],
                "ours": our[key],
                "simfoundryMesh": sim_sam3d[key]["mesh"],
            }
            for key, title, _ in SAM3D_CASES
        ],
    }
    data["simfoundryCompare"] = [
        {
            "key": f"hybrid_{item['key']}",
            "title": item["title"],
            "mode": "hybrid",
            "input": item["input"],
            "ours": item["ours"],
            "simfoundryTitle": item["simfoundryTitle"],
            "simfoundry": item["simfoundry"],
        }
        for item in data["hybridCompare"]
    ] + [
        {
            "key": f"digital_{item['key']}",
            "title": item["title"],
            "mode": "video",
            "input": item["input"],
            "ours": item["ours"],
            "simfoundryTitle": "Reconstructed Twins",
            "simfoundryVideo": item["simfoundryVideo"],
        }
        for item in data["digitalCompare"]
    ] + [
        {
            "key": f"sam3d_{item['key']}",
            "title": item["title"],
            "mode": "mesh",
            "input": item["input"],
            "ours": item["ours"],
            "simfoundryTitle": "SimFoundry Foreground",
            "simfoundryMesh": item["simfoundryMesh"],
        }
        for item in data["sam3dCompare"]
    ]
    DATA_JS.write_text(
        "export const PAGE_DATA = "
        + json.dumps(data, indent=2, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )
    sanitize_publish_assets()
    print(json.dumps({
        "our_scenes": len(our),
        "reconstructed_scenes": len(reconstructed),
        "simfoundry_hybrid": len(sim_hybrid),
        "simfoundry_videos": len(sim_videos),
        "sam3d": len(sim_sam3d),
        "assets_dir": str(ASSETS),
    }, indent=2))


if __name__ == "__main__":
    main()
