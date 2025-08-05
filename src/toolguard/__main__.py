#important to load the env variables BEFORE policy_adherence library (so programmatic_ai configuration will take place)
import dotenv
dotenv.load_dotenv()

from .cli import main

if __name__ == "__main__":
    main()