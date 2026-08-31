import * as React from 'react';
import { forwardRef } from 'react';
import { AppBar, UserMenu, MenuItemLink, ToggleThemeButton, useTranslate } from 'react-admin';
import Typography from '@mui/material/Typography';
import SettingsIcon from '@mui/icons-material/Settings';

import Logo from './Logo';

const ConfigurationMenu = forwardRef((props, ref) => {
    const translate = useTranslate();
    return (
        <MenuItemLink
            ref={ref}
            to="/configuration"
            primaryText="Configuration"
            leftIcon={<SettingsIcon />}
            onClick={props.onClick}
            sidebarIsOpen
        />
    );
});

const CustomUserMenu = (props) => (
    <UserMenu {...props}>
        <ConfigurationMenu />
    </UserMenu>
);

const CustomAppBar = (props) => (
    <AppBar {...props} elevation={1} userMenu={<CustomUserMenu />} toolbar={<ToggleThemeButton />}>
        <Typography
            variant="h6"
            color="inherit"
            id="react-admin-title"
            sx={{
                flex: 1,
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
            }}
        />
        <Logo />
        <span style={{ flex: 1 }} />
    </AppBar>
);

export default CustomAppBar;
