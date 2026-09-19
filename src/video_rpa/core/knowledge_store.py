"""Video RPA 知識庫管理器 - 負責步驟定位器與彈窗規則的持久化與動態演化."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """Manages persistent storage and dynamic evolution of step locators and popups."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data: Dict[str, Any] = {"version": "1.0.0", "steps": {}, "known_popups": []}
        self.load()

    def load(self) -> None:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info(f"Loaded knowledge store from {self.file_path}")
            except Exception as e:
                logger.error(f"Failed to load knowledge store from {self.file_path}: {e}")
        else:
            logger.info(f"Knowledge file {self.file_path} does not exist yet. Initializing new store.")
            self.save()

    def save(self) -> bool:
        try:
            folder = os.path.dirname(self.file_path)
            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)

            temp_path = f"{self.file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.file_path)
            logger.info(f"Persisted knowledge store to {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save knowledge store to {self.file_path}: {e}")
            return False

    def get_platform(self) -> str:
        """Returns the platform name associated with this knowledge store."""
        if "platform" in self.data and self.data["platform"]:
            return self.data["platform"]
        basename = os.path.basename(self.file_path)
        if "_" in basename:
            return basename.split("_")[0]
        return os.path.splitext(basename)[0]

    def get_step(self, step_id: str) -> Optional[Dict[str, Any]]:
        return self.data.get("steps", {}).get(step_id)

    def get_locators(self, step_id: str) -> List[Dict[str, Any]]:
        step = self.get_step(step_id)
        if not step:
            return []
        locators = step.get("locators", [])
        # Return sorted by weight descending
        return sorted(locators, key=lambda x: x.get("weight", 0), reverse=True)

    def promote_locator_to_primary(self, step_id: str, locator_value: str) -> None:
        """Promotes the given locator to the 1st position with highest weight,
        ensuring it will be matched on the first attempt in future runs."""
        step = self.get_step(step_id)
        if not step:
            return

        locators = step.get("locators", [])
        target_loc = None
        for loc in locators:
            if loc.get("value") == locator_value:
                target_loc = loc
                break

        if target_loc:
            current_max_weight = max((l.get("weight", 0) for l in locators), default=10)
            target_loc["weight"] = max(target_loc.get("weight", 0), current_max_weight + 5)
            locators.remove(target_loc)
            locators.insert(0, target_loc)
            self.save()
            logger.info(f"Promoted locator to primary for [{step_id}]: {locator_value} (new weight: {target_loc['weight']})")

    def record_success(self, step_id: str, locator_value: str, is_secondary: bool = False) -> None:
        """Boosts weight of the successful locator. If it was a secondary hit, promotes it directly to primary."""
        if is_secondary:
            self.promote_locator_to_primary(step_id, locator_value)
            return

        step = self.get_step(step_id)
        if not step:
            return

        locators = step.get("locators", [])
        updated = False
        for loc in locators:
            if loc.get("value") == locator_value:
                loc["weight"] = loc.get("weight", 5) + 2
                updated = True
                break

        if updated:
            self.save()

    def add_or_update_locator(self, step_id: str, by_type: str, value: str, weight: Optional[int] = None) -> None:
        """Inserts a new learned locator or updates an existing one with highest priority."""
        if "steps" not in self.data:
            self.data["steps"] = {}

        if step_id not in self.data["steps"]:
            self.data["steps"][step_id] = {
                "name": step_id,
                "timeout": 10,
                "optional": False,
                "locators": []
            }

        locators = self.data["steps"][step_id].setdefault("locators", [])
        current_max = max((l.get("weight", 0) for l in locators), default=10)
        target_weight = weight if weight is not None else current_max + 5

        for loc in locators:
            if loc.get("value") == value:
                loc["weight"] = max(loc.get("weight", 0), target_weight)
                locators.remove(loc)
                locators.insert(0, loc)
                self.save()
                return

        # Insert new locator with highest priority at position 0
        locators.insert(0, {"by": by_type, "value": value, "weight": target_weight})
        self.save()
        logger.info(f"Learned and persisted new primary locator for [{step_id}]: {by_type}={value} (weight: {target_weight})")

    def add_step(self, step_id: str, name: str, locators: List[Dict[str, Any]],
                 timeout: int = 10, optional: bool = False) -> None:
        """Registers a new step dynamically learned during RPA execution."""
        if "steps" not in self.data:
            self.data["steps"] = {}

        self.data["steps"][step_id] = {
            "name": name,
            "timeout": timeout,
            "optional": optional,
            "locators": locators
        }
        self.save()
        logger.info(f"Added new step [{step_id}]: {name}")

    def get_known_popups(self) -> List[Dict[str, Any]]:
        return self.data.get("known_popups", [])

    def add_known_popup(self, name: str, detect_xpath: str, action: str, target_xpath: str) -> None:
        popups = self.data.setdefault("known_popups", [])
        for p in popups:
            if p.get("detect_xpath") == detect_xpath:
                p["target_xpath"] = target_xpath
                self.save()
                return

        popups.append({
            "name": name,
            "detect_xpath": detect_xpath,
            "action": action,
            "target_xpath": target_xpath
        })
        self.save()
        logger.info(f"Added new known popup: {name}")
