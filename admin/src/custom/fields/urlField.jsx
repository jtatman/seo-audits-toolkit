import * as React from "react";
import { useRecordContext } from 'react-admin';
import LaunchIcon from '@mui/icons-material/Launch';

const MyUrlField = ({ source }) => {
    const record = useRecordContext();
    if (!record) return null;
    return (
        <a
            href={record[source]}
            target="_blank"
            rel="noreferrer"
            style={{ textDecoration: 'none', color: 'grey' }}
        >
            {record[source]}
            <LaunchIcon sx={{ width: '0.5em', paddingLeft: '2px' }} />
        </a>
    );
}

export default MyUrlField;
