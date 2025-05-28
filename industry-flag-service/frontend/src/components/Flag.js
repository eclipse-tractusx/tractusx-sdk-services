/*
  Tractus-X - Industry Flag Service

  Copyright (c) 2025 CGI Deutschland B.V. & Co. KG
  Copyright (c) 2025 Contributors to the Eclipse Foundation

  See the NOTICE file(s) distributed with this work for additional
  information regarding copyright ownership.

  This program and the accompanying materials are made available under the
  terms of the Apache License, Version 2.0 which is available at
  https://www.apache.org/licenses/LICENSE-2.0.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
  either express or implied. See the
  License for the specific language govern in permissions and limitations
  under the License.

  SPDX-License-Identifier: Apache-2.0
*/

import * as React from "react";
import Card from "@mui/material/Card";
import CardActions from "@mui/material/CardActions";
import CardContent from "@mui/material/CardContent";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import DownloadIcon from "@mui/icons-material/Download";
import { CardHeader } from "@mui/material";
import Box from "@mui/material/Box";
import { setMessage } from "../managers/StateManager";
import { useDispatch } from "react-redux";
import {
  BACKEND_URL,
  API_KEY,
  ENDPOINT_GET_FLAG_PROOF_BY_BPN,
  ENDPOINT_GET_MY_FLAGS,
} from "../services/service.const";
import DownloadFlagService from "../services/DownloadFlagService";

export default function Flag({ id, flag, bpn }) {
  // create backend service instance to make API calls
  const dispatch = useDispatch();
  const downloadFlagService = new DownloadFlagService();

  const onDownload = async (id) => {
    const headers = {
      "X-Api-Key": API_KEY,
    };
    try {
      // Check if bpn value is "My Company Flags", then download my flags
      if (bpn === "My Company Flags") {
        // same company => my company flag
        const downloadUrl = BACKEND_URL + ENDPOINT_GET_MY_FLAGS + "/" + id;
        // Trigger download my company flag
        let response = await downloadFlagService.downloadMyCompanyFlag(
          "GET",
          downloadUrl,
          headers,
          id
        );
        if (response.status)
          dispatch(setMessage("The flag " + id + " is being downloaded..!!"));
        else
          dispatch(
            setMessage(
              "There was an error downloading the flag: " + id + "..!!"
            )
          );
      } else {
        // different company => partner company flag
        // Trigger download partner company flag
        const downloadUrl = BACKEND_URL + ENDPOINT_GET_FLAG_PROOF_BY_BPN;
        const data = {
          bpn: bpn,
          id: id,
        };
        let response = await downloadFlagService.downloadPartnerCompanyFlag(
          "POST",
          downloadUrl,
          headers,
          data
        );
        if (response.status)
          dispatch(setMessage("The flag " + id + " is being downloaded..!!"));
        else
          dispatch(
            setMessage(
              "There was an error downloading your partner company flag: " +
                id +
                "..!!"
            )
          );
      }
    } catch (error) {
      console.error("Error downloading flag:", error);
    }
  };

  return (
    <div>
      <Card sx={{ border: 1 }}>
        <CardHeader
          sx={{
            height: 100,
            flexFlow: 0,
          }}
          title={flag.name}
          titleTypographyProps={{ variant: "h6" }}
          subheader={flag.type}
        />

        <CardContent>
          <Box>
            <Typography sx={{ color: "text.secondary" }}>Type</Typography>
            <Typography variant="body2">{flag.type}</Typography>
          </Box>
          <Box sx={{ mt: 1.5 }}>
            <Typography sx={{ color: "text.secondary" }}>ID</Typography>
            <Typography variant="body2">{id}</Typography>
          </Box>
        </CardContent>

        {flag.mimetype !== "Boolean" ? (
          <CardActions>
            <Button
              fullWidth
              variant="outlined"
              onClick={(event) => {
                onDownload(id);
              }}
              endIcon={<DownloadIcon />}
            >
              Download
            </Button>
          </CardActions>
        ) : (
          <CardActions sx={{ height: 37 }}></CardActions>
        )}
      </Card>
    </div>
  );
}
