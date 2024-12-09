# Trading BTC Perpetual Deribit 


This repository contains the code for a system designed to generate trade signals for the Bitcoin perpetual futures market. These signals are then stored in a database.

## Table of contents

- [Project Description](#project-description)
- [Requirements](#requirements)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Contributing](#contributing)

## Project Description

The project uses Python to interact with the Deribit API, generate trading signals based on market data, and store these signals in a BigQuery database for future analysis.

## Requirements

Python 3.x is required to run the project. Other dependencies are listed in the `requirements.txt` file.

## Installation

To install the project:

1. Ensure Python 3.x is installed.
2. Install the required dependencies by running `pip install -r requirements.txt` in your terminal.

## Project Structure

- `main.py`: This is the main script for the project. It calls functions from `deribit_utils.py` to interact with the Deribit API, generate trading signals, and use the resulting data to write into the BigQuery table.

- `gcp_utils/secret_manager.py`: This script is responsible for managing confidential data like API keys or other credentials. It ensures that these credentials are stored securely and are accessible to other scripts when needed. It strongly supports Google Cloud Secret Manager.

- `deribit_utils/deribit_utils.py`: This file contains functions for interacting with the Deribit API, such as sending requests to the API for data, processing API responses, and error handling. It’s here where the main trading logic happens.

The `infra` folder contains Terraform files like `backend.tf`, `pubsub.tf`, and `variables.tf` which are used for defining and creating the infrastructure environment for the project. 

The `cloudbuild.yaml` file is used by Google Cloud Build for automatic deployments.

## Usage

Describe how to use the application here. For example, how to run the `main.py` script.

## Contributing

Share guidelines on how others can contribute to your project. Include any preferred coding styles, branches, unit tests, pull request strategies, etc.

The README file should provide a detailed overview of your project, its structure, and how to use and contribute to it.xit signals and write data into the BigQuery table.