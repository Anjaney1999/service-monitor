terraform {
  cloud {
    organization = "<organization>"

    workspaces {
      name = "<workspace>"
    }
  }
}

provider "aws" {
  region  = "eu-west-2"
}


