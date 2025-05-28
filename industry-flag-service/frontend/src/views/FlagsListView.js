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

import React from "react";
import { Container, Grid } from "@mui/material";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Flag from "../components/Flag";
import { useSelector } from "react-redux";
import { selectPrint } from "../managers/StateManager";

export default function FlagsListView({ value, companyFlags }) {
  const showFlags = useSelector(selectPrint);

  return (
    <Container sx={{ border: 0, px: "1rem", pt: "1rem", pb: "5rem" }}>
      {companyFlags.length > 0 ? (
        <Box>
          <Typography
            variant="h5"
            noWrap
            sx={{
              mx: "auto",
              flexGrow: 1,
              fontWeight: 700,
              letterSpacing: ".1rem",
              color: "inherit",
              textDecoration: "none",
              textAlign: "center",
            }}
          >
            {value === "My Company Flags" ? value : value + " Company Flags"}
          </Typography>
        </Box>
      ) : null}
      <br />
      {showFlags ? (
        <Box>
          <Grid container spacing={3}>
            {companyFlags.map(([id, data]) => (
              <Grid item key={id} xs={12} md={4} lg={3}>
                <Flag id={id} flag={data} bpn={value}></Flag>
                {/* {value === "My Company Flags" ? (
                  <MyCompanyFlag id={id} flag={data} bpn={value} />
                ) : (
                  <CompanyFlag id={id} flag={data} bpn={value} />
                )} */}
              </Grid>
            ))}
          </Grid>
        </Box>
      ) : null}
    </Container>
  );
}
