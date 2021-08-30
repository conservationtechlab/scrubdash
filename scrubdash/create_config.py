import scrubdash as scrubdash


def main():
    scrubdash_path = scrubdash.__path__[0]
    config_file = scrubdash_path + '/cfgs/config.yaml.example'

    with open(config_file) as config:
        lines = config.readlines()
        example_config = open('config.yaml.example', 'w')
        for line in lines:
            example_config.write(line)
        example_config.close()


if __name__ == "__main__":
    main()
