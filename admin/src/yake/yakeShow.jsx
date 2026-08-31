import * as React from "react";
import { ArrayField, Datagrid, DeleteButton, EditButton, Show, SimpleShowLayout, TextField } from 'react-admin';



export const YakeShow = (props) => {

    return (
        <Show {...props}>
            <SimpleShowLayout>
                <TextField source="id" />
                <TextField source="name" />
                <ArrayField source="result" fieldKey="id">
                    <Datagrid>
                        <TextField source="ngram" />
                        <TextField source="score"/>
                    </Datagrid>
                </ArrayField>
                <EditButton />
                <DeleteButton />
            </SimpleShowLayout>
        </Show>
    )
};