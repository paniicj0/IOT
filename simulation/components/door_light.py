def create_door_light(settings):
    if settings["simulated"]:
        from simulators.door_light import light_on, light_off
        return light_on, light_off
    else:
        from actuators.door_light import DoorLight
        light = DoorLight(settings["pin"])
        return light.on, light.off
