import aia_utiilities_test as au

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
PREFIX_INPUT = "prices"
PREFIX_OUTPUT = "algos"

# Main scaffolding for viz2
def main():
    r = au.Redis_Utilities(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    prefix_input = f"{PREFIX_INPUT}:*"  
    prefix_output = f"{PREFIX_OUTPUT}:*"

    result = r.read_all(prefix_input)

    # print(result)
    for r in result:
        print(r)
    # r.clear(prefix_output)


if __name__ == "__main__":
	main()
