from selah_brain import handle_command

print("\n💬 SELAH Text Mode (type 'exit' to quit)\n")

while True:
    user_input = input("You: ").strip()

    if user_input.lower() in ["exit", "quit"]:
        print("SELAH: Goodbye 👋")
        break

    handle_command(user_input, speak_out=False)
