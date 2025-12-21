def create_buzzer(settings):
    if settings["simulated"]:
        from simulators.buzzer import buzzer_on, buzzer_off
        return buzzer_on, buzzer_off
    else:
        from actuators.buzzer import Buzzer
        buzzer = Buzzer(settings["pin"])
        return buzzer.on, buzzer.off
