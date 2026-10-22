from src.agent import Agent

def main():
    print("🤖 ZentroMart AI Assistant is ready. Type 'quit' to exit.\n")
    agent = Agent(voice=False)
    
    while True:
        user_input = input("👤 YOU: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        reply, meta = agent.respond(user_input)
        print(f"\n🤖 AGENT: {reply}")
        print(f"[Sources: {meta.get('sources', [])}]\n")

if __name__ == "__main__":
    main()