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

    def get_step(self, step_id: str) -> Optional[Dict[str, Any]]:
        return self.data.get("steps", {}).get(step_id)

    def get_locators(self, step_id: str) -> List[Dict[str, Any]]:
        step = self.get_step(step_id)
        if not step:
            return []
        locators = step.get("locators", [])
        # Return sorted by weight descending
        return sorted(locators, key=lambda x: x.get("weight", 0), reverse=True)

    def record_success(self, step_id: str, locator_value: str) -> None:
        """Boosts weight of the successful locator to prioritize it in subsequent runs."""
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

    def add_or_update_locator(self, step_id: str, by_type: str, value: str, weight: int = 15) -> None:
        """Inserts a new learned locator or updates an existing one with high weight."""
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
        for loc in locators:
            if loc.get("value") == value:
                loc["weight"] = max(loc.get("weight", 0), weight)
                self.save()
                return

        # Insert new locator with high priority
        locators.insert(0, {"by": by_type, "value": value, "weight": weight})
        self.save()
        logger.info(f"Learned and persisted new locator for [{step_id}]: {by_type}={value}")

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
