import Collapse from '@mui/material/Collapse';
import List from '@mui/material/List';
import ListItemIcon from '@mui/material/ListItemIcon';
import MenuItem from '@mui/material/MenuItem';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import ExpandMore from '@mui/icons-material/ExpandMore';
import * as React from 'react';
import { Fragment } from 'react';

const sidebarListSx = (sidebarIsOpen) => ({
    '& a': {
        paddingLeft: sidebarIsOpen ? 4 : 2,
        transition: 'padding-left 195ms cubic-bezier(0.4, 0, 0.6, 1) 0ms',
    },
});

export const SubMenu = ({
    handleToggle,
    sidebarIsOpen,
    isOpen,
    name,
    icon,
    children,
    dense,
}) => {
    const header = (
        <MenuItem dense={dense} onClick={handleToggle}>
            <ListItemIcon sx={{ minWidth: (theme) => theme.spacing(5) }}>
                {isOpen ? <ExpandMore /> : icon}
            </ListItemIcon>
            <Typography variant="inherit" color="textSecondary">
                {name}
            </Typography>
        </MenuItem>
    );

    return (
        <Fragment>
            {sidebarIsOpen || isOpen ? (
                header
            ) : (
                <Tooltip title={name} placement="right">
                    {header}
                </Tooltip>
            )}
            <Collapse in={isOpen} timeout="auto" unmountOnExit>
                <List
                    dense={dense}
                    component="div"
                    disablePadding
                    sx={sidebarListSx(sidebarIsOpen)}
                >
                    {children}
                </List>
            </Collapse>
        </Fragment>
    );
};
