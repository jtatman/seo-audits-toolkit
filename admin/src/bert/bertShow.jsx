import * as React from "react";
import { SimpleShowLayout, Show, TextField } from 'react-admin';


export const BertShow = (props) => (
    <Show {...props}>
        <SimpleShowLayout>
            <TextField source="result" />
            <TextField source="text" />
        </SimpleShowLayout>
    </Show>
);
