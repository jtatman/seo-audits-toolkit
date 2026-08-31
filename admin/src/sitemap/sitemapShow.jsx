import * as React from "react";
import { ArrayField, useRecordContext, Datagrid, DateField, DeleteButton, EditButton, Show, SimpleShowLayout, TextField, UrlField } from 'react-admin';
import { Link } from 'react-router-dom';
import Button from '@mui/material/Button';

const CreateRelatedCommentButton = () => {
    const record = useRecordContext();
    if (!record) return null;
    return (
        <Button
            component={Link}
            to="/extractor/create"
            state={{ record: { url: record.url, website_name: record.org } }}
        >
            Extract Headers/Images/Links
        </Button>
    );
}



export const SitemapShow = (props) => {
    return (
        <Show {...props}>
            <SimpleShowLayout>
                <TextField source="id" />
                <TextField source="url" />
                <ArrayField source="result" fieldKey="id" >
                    <Datagrid>
                        <UrlField source="url" />
                        <DateField source="last_modified" showTime={true}/>
                        <CreateRelatedCommentButton/>
                    </Datagrid>
                </ArrayField>
                <EditButton />
                <DeleteButton />
            </SimpleShowLayout>
        </Show>
    )
};
