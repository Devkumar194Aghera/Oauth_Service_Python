import { useState } from "react";
import { Box, Autocomplete, TextField } from "@mui/material";
import { AirtableIntegration } from "./integrations/airtable";
import { NotionIntegration } from "./integrations/notion";
import { HubspotIntegration } from "./integrations/hubspot";
import { DataForm } from "./data-form";

// run npm i to install all required pakages

const integrationMapping = {
  Notion: NotionIntegration,
  Airtable: AirtableIntegration,
  Hubspot: HubspotIntegration,
};

export const IntegrationForm = () => {
  const [integrationParams, setIntegrationParams] = useState({});
  const [user, setUser] = useState("TestUser");
  const [org, setOrg] = useState("TestOrg");
  const [currType, setCurrType] = useState(null);
  const CurrIntegration = integrationMapping[currType];

  return (
    <>
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        flexDirection="column"
        width="100%"
        sx={{ width: "100%" }}
      >
        <Box flexDirection="column" width="auto">
          <TextField
            label="User"
            value={user}
            onChange={(e) => setUser(e.target.value)}
            sx={{ mt: 2 }}
          />
          <TextField
            label="Organization"
            value={org}
            onChange={(e) => setOrg(e.target.value)}
            sx={{ mt: 2 }}
            style={{ marginLeft: "12px" }}
          />
          <Autocomplete
            id="integration-type"
            options={Object.keys(integrationMapping)}
            sx={{ width: "auto", mt: 2 }}
            renderInput={(params) => (
              <TextField {...params} label="Integration Type" />
            )}
            onChange={(e, value) => setCurrType(value)}
          />
        </Box>
      </Box>
      {currType && (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          flexDirection={"column"}
          sx={{ mt: 2 }}
        >
          {currType && (
            <Box>
              <CurrIntegration
                user={user}
                org={org}
                integrationParams={integrationParams}
                setIntegrationParams={setIntegrationParams}
              />
            </Box>
          )}
          {integrationParams?.credentials && currType && (
            <Box display="flex" justifyContent="center" alignItems="center">
              <DataForm
                integrationType={integrationParams?.type}
                credentials={integrationParams?.credentials}
              />
            </Box>
          )}
        </Box>
      )}
    </>
  );
};
