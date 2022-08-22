terraform {
  cloud {
    organization = "anjie-test"

    workspaces {
      name = "gh-actions"
    }
  }
}

provider "aws" {
  region  = "eu-west-2"
}


