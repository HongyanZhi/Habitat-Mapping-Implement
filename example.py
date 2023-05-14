from habitat.datasets.object_nav.object_nav_dataset import (
        ObjectNavDatasetV1,
    )
from typing import List, Optional
from habitat.core.registry import registry
from habitat.tasks.nav.nav import (
    ShortestPathPoint,
)
from habitat.config.default import get_config
from habitat.core.registry import registry
from habitat.datasets.pointnav.pointnav_dataset import (
    CONTENT_SCENES_PATH_FIELD,
    DEFAULT_SCENE_PATH_PREFIX,
)
from habitat.config import Config
CONTENT_SCENES_PATH_FIELD = "content_scenes_path"
DEFAULT_SCENE_PATH_PREFIX = "data/scene_datasets/"
from habitat.datasets.vln.r2r_vln_dataset import VLNDatasetV1
from habitat.tasks.nav.object_nav_task import (
    ObjectGoalNavEpisode,
)
import json
import os
from tools import Application, Action_Space
import habitat
from habitat.config.default import get_config
from habitat.datasets import make_dataset
import zson.dataset
import matplotlib.pyplot as plt
from habitat.tasks.nav.shortest_path_follower import ShortestPathFollower
import numpy as np

@registry.register_dataset(name="ObjectNav-v3")
class ObjectNavDatasetV3(ObjectNavDatasetV1):
    '''r
    处理gibson episode id冲突问题
    '''
    def __init__(self, config: Optional[Config] = None) -> None:
        super().__init__(config)
        
    def from_json(
        self, json_str: str, scenes_dir: Optional[str] = None
    ) -> None:
        deserialized = json.loads(json_str)
        if CONTENT_SCENES_PATH_FIELD in deserialized:
            self.content_scenes_path = deserialized[CONTENT_SCENES_PATH_FIELD]

        if "category_to_task_category_id" in deserialized:
            self.category_to_task_category_id = deserialized[
                "category_to_task_category_id"
            ]

        if "category_to_scene_annotation_category_id" in deserialized:
            self.category_to_scene_annotation_category_id = deserialized[
                "category_to_scene_annotation_category_id"
            ]

        if "category_to_mp3d_category_id" in deserialized:
            self.category_to_scene_annotation_category_id = deserialized[
                "category_to_mp3d_category_id"
            ]

        assert len(self.category_to_task_category_id) == len(
            self.category_to_scene_annotation_category_id
        )

        assert set(self.category_to_task_category_id.keys()) == set(
            self.category_to_scene_annotation_category_id.keys()
        ), "category_to_task and category_to_mp3d must have the same keys"

        if len(deserialized["episodes"]) == 0:
            return

        if "goals_by_category" not in deserialized:
            deserialized = self.dedup_goals(deserialized)

        for k, v in deserialized["goals_by_category"].items():
            self.goals_by_category[k] = [self._ObjectNavDatasetV1__deserialize_goal(g) for g in v]

        for i, episode in enumerate(deserialized["episodes"]):
            episode = ObjectGoalNavEpisode(**episode)
            # episode.episode_id = self.global_unique_id
            # self.global_unique_id += 1

            if scenes_dir is not None:
                if episode.scene_id.startswith(DEFAULT_SCENE_PATH_PREFIX):
                    episode.scene_id = episode.scene_id[
                        len(DEFAULT_SCENE_PATH_PREFIX) :
                    ]

                episode.scene_id = os.path.join(scenes_dir, episode.scene_id)

            episode.goals = self.goals_by_category[episode.goals_key]
            episode.scene_dataset_config = 'data/scene_datasets/mp3d/mp3d.scene_dataset_config.json'
            if episode.shortest_paths is not None:
                for path in episode.shortest_paths:
                    for p_index, point in enumerate(path):
                        if point is None or isinstance(point, (int, str)):
                            point = {
                                "action": point,
                                "rotation": None,
                                "position": None,
                            }

                        path[p_index] = ShortestPathPoint(**point)

            self.episodes.append(episode)  # type: ignore [attr-defined]

def test_single_semantic_occupied_map():
    # create an habitat environment for test
    config = get_config("tools/cooardinate_transformation_tool_for_haibitat/habitat_mp3d_object_nav_test.yaml")
    dataset = make_dataset(
        id_dataset=config.DATASET.TYPE, config=config.DATASET
    )
    with habitat.Env(config=config, dataset=dataset) as env:
        obs = env.reset()
        depth_img = obs['depth']
        semantic_img = obs['semantic']
        
        # examples for all application
        app = Application((256,256), 90, 1, 0.005, 400, 0.5, 1, 2)
        occupied_map = app.parse_depth_topdownmap(depth_img)
        semantic_map = app.parse_semantic_topdownmap(depth_img, semantic_img)
        plt.imsave("./occupied_map.png", occupied_map)
        plt.imsave("./semantic_map.png", semantic_map)
        plt.imsave("./rgb.png", obs['rgb'])
        plt.imsave("./depth.png", obs['depth'].reshape(obs['depth'].shape[0], obs['depth'].shape[1]))
        plt.imsave("./semantic.png", obs['semantic'])
        pass
    
def test_update_semantic_occupied_map_by_action():
    # create an habitat environment for test
    config = get_config("tools/cooardinate_transformation_tool_for_haibitat/habitat_mp3d_object_nav_test.yaml")
    dataset = make_dataset(
        id_dataset=config.DATASET.TYPE, config=config.DATASET
    )
    with habitat.Env(config=config, dataset=dataset) as env:
        
        goal_radius = env.episodes[0].goals[0].radius
        if goal_radius is None:
            goal_radius = config.SIMULATOR.FORWARD_STEP_SIZE
        follower = ShortestPathFollower(
            env._sim, goal_radius, False
        )
        
        obs = env.reset()
        depth_img = obs['depth']
        semantic_img = obs['semantic']

        app = Application((256,256), 90, 1, 0.005, 2000, 0.5, 1, 2)
        occupied_map = app.parse_depth_topdownmap(depth_img)
        semantic_map = app.parse_semantic_topdownmap(depth_img, semantic_img)
        
        while not env.episode_over:
            best_action = follower.get_next_action(
                env.current_episode.goals[0].position
            )
            if best_action is None:
                break

            obs = env.step(best_action)
            depth_img = obs['depth']
            semantic_img = obs['semantic']
            app.update_pos2map_by_action(0.025, 30, best_action)
            new_occupied_map = app.parse_depth_topdownmap(depth_img)
            new_semantic_map = app.parse_semantic_topdownmap(depth_img, semantic_img)
            occupied_map = app.update_occupied_map(new_occupied_map, occupied_map)
            semantic_map = app.update_semantic_map(new_semantic_map, semantic_map)

            
        plt.imsave("./occupied_map.png", occupied_map)
        plt.imsave("./semantic_map.png", semantic_map)
        # plt.imsave("./rgb.png", obs['rgb'])
        # plt.imsave("./depth.png", obs['depth'].reshape(obs['depth'].shape[0], obs['depth'].shape[1]))
        # plt.imsave("./semantic.png", obs['semantic'])
        pass

def test_update_semantic_occupied_map_by_position():
    # create an habitat environment for test
    config = get_config("tools/cooardinate_transformation_tool_for_haibitat/habitat_mp3d_object_nav_test.yaml")
    dataset = make_dataset(
        id_dataset=config.DATASET.TYPE, config=config.DATASET
    )
    with habitat.Env(config=config, dataset=dataset) as env:
        
        goal_radius = env.episodes[0].goals[0].radius
        if goal_radius is None:
            goal_radius = config.SIMULATOR.FORWARD_STEP_SIZE
        follower = ShortestPathFollower(
            env._sim, goal_radius, False
        )
        
        obs = env.reset()
        depth_img = obs['depth']
        semantic_img = obs['semantic']

        app = Application((256,256), 90, 1, 0.005, 2000, 0.5, 1, 2)
        occupied_map = app.parse_depth_topdownmap(depth_img)
        semantic_map = app.parse_semantic_topdownmap(depth_img, semantic_img)
        
        position = env._sim.get_agent_state().position.tolist()
        rotation = env._sim.get_agent_state().rotation
        app.update_pos2map_by_cooardinate(position, rotation)
        
        while not env.episode_over:
            best_action = follower.get_next_action(
                env.current_episode.goals[0].position
            )
            if best_action is None:
                break

            obs = env.step(best_action)
            # print("best_action", best_action)
            depth_img = obs['depth']
            semantic_img = obs['semantic']
            position = env._sim.get_agent_state().position.tolist()
            rotation = env._sim.get_agent_state().rotation
            app.update_pos2map_by_cooardinate(position, rotation)
            new_occupied_map = app.parse_depth_topdownmap(depth_img)
            new_semantic_map = app.parse_semantic_topdownmap(depth_img, semantic_img)
            occupied_map = app.update_occupied_map(new_occupied_map, occupied_map)
            semantic_map = app.update_semantic_map(new_semantic_map, semantic_map)
            # print(f"map pos {app.pos2map.x},{app.pos2map.y},{app.pos2map.heading}")
            # print(f"world pos {app.pos2world.x},{app.pos2world.z},{app.pos2world.heading}")
            
        plt.imsave("./occupied_map.png", occupied_map)
        plt.imsave("./semantic_map.png", semantic_map)
        # plt.imsave("./rgb.png", obs['rgb'])
        # plt.imsave("./depth.png", obs['depth'].reshape(obs['depth'].shape[0], obs['depth'].shape[1]))
        # plt.imsave("./semantic.png", obs['semantic'])
        pass

if __name__ == '__main__':
    test_update_semantic_occupied_map_by_position()