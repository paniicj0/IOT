def actuator_menu(light_on, light_off, buzzer_on, buzzer_off):
    while True:
        print("\n=== PI1 ACTUATOR CONTROL ===")
        print("1 - Turn ON door light")
        print("2 - Turn OFF door light")
        print("3 - Activate buzzer")
        print("4 - Deactivate buzzer")
        print("0 - Exit")
        choice = input("Choose option: ")

        if choice == "1":
            light_on()
        elif choice == "2":
            light_off()
        elif choice == "3":
            buzzer_on()
        elif choice == "4":
            buzzer_off()
        elif choice == "0":
            break
        else:
            print("Invalid option")
