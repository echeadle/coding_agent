from nanocode import Agent, AgentStop

def main():
    agent = Agent()
    print("Nanocode v0.1 initialized.")
    print("Type  /q to quit.")
    
    while True:
        try:
            user_input = input("\n> ")
            output = agent.handle_input(user_input)
            if output:
                print(output)
                
        except (AgentStop, KeyboardInterrupt):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
