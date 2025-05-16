<!--
#######################################################################

Tractus-X - Industry Flag Service 

Copyright (c) 2025 CGI Deutschland B.V. & Co. KG
Copyright (c) 2025 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This work is made available under the terms of the
Creative Commons Attribution 4.0 International (CC-BY-4.0) license,
which is available at
https://creativecommons.org/licenses/by/4.0/legalcode.

SPDX-License-Identifier: CC-BY-4.0

#######################################################################
-->

## Industry Flag Service UI

### Introduction

This document describes the industry flag service UI component that is used to request and show partner/your company flags based on Business Partner Number (BPN number) using the backend system and EDCs. The application is developed in Reactjs technology using Material UI (MUI) design framework.

### Features

The app implements the following features:

#### Search View

It allows you to search for partner company flags by the their BPN. Since the BPNL has a specific format BPNLXXXXXXXXXXXX (x: alphanumeric characters) with 12 digits length, the app validates the BPN using regex pattern matching  `/^BPNL[A-Z0-9]{12}$/`.

#### Back Button

The Back button is visible when the flags are loaded and displayed in the Display view. It hides the search view and to make a focus on the flags retrieved.

#### Display View

It allows you to display response from the flag management backend system that is coming from the partner company using EDCs. Each flag contains thefollowing data attritutes: 

- Flag Name ("industry")
- MimeType (JSON, Boolean)
- Flag Type (Boolean)
- ID (UUID of the flag)

#### Downloading a Flag:

It allows you to download/export the choosen flag shown in the Display View. Currently, it downloads the flag content in a simple txt file.

#### Request My Company Flags

It feature allows you to request your own company flags from the top right menu bar (User profile).

## Deployment

The deployment is available in [Helm Chart](../charts/industry-flag-service/) to be hosted in container platform such as Kubernetes environment.

> Note: The app is running on nginx and accessible at a port 80


## Local Run

In the project directory, install the dependencies

### `npm install`

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

