
# Introduction 
A library of various mapping function for habitat<https://github.com/HongyanZhi/Habitat-Mapping-Implement.git> platform

## Map Coordinate System
TopDownMap Coordinate System : The coordinate center maybe locates somewhere in the world
![Input](figures/TopDownMapCoordinate.png)  
OccupiedMap Coordinate System  : The coordinate center locates on the left-top of the image
![Input](figures/OccupiedMapCoordinate.png)  

## Application Overview
### Input : RGB,DEPTH,SEMANTIC
![Input](figures/Input.png)
### Output:     
OccupiedMap : project the depth image into the top down map    
![Input](figures/OccupiedMap.png)  
SemanticOccupiedMap : project the semantic image into the top down map which each pixels has some semantic meanings  
![Input](figures/SemanticOccupiedMap.png)    
SceneObjectList : Object average coordinate based on current observation 
![Input](figures/SceneObjectList.jpg)        

# Notation
1. Depth image as input must be in the scale of 10 meters, which is the default setting of DEPEH_SENSOR
2. Please carefully check if the semantic images corresponding to the rgb images
3. This library is suitable both for discrete and continuous enviroment; Please update the agent location by position in discrete environment and update the agent location by position or action in  continuous environment 

# Example
Please run the demo functions in example.py and view the reference visualization in folder visualization. Example test on **v0.2.1** both for habitat-lab and habitat-sim


# Usage
1. Init   
```python
app = Application((image_width, image_height), fov, depth_threshold, resolution_meter2pixel, occupied_map_size, camera_height, free_index, occupied_index)
```
2. Api
```python
# parse occupied map
occupied_map = app.parse_depth_topdownmap(depth_img)
# parse semantic occupied map
semantic_map = app.parse_semantic_topdownmap(depth_img, semantic_img)
# update agent location by coordinate
position = env._sim.get_agent_state().position.tolist()
rotation = env._sim.get_agent_state().rotation
app.update_pos2map_by_cooardinate(position, rotation)
# update agent location by action
app.update_pos2map_by_action(forward_step2tenmeter, turn_angle2degree, action)
# stack new map to old map
occupied_map = app.update_occupied_map(new_occupied_map, old_occupied_map)
semantic_map = app.update_semantic_map(new_semantic_map, old_semantic_map)
```