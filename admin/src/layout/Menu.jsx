import { Box, useMediaQuery } from '@mui/material';
import DomainIcon from '@mui/icons-material/Domain';
import HighlightIcon from '@mui/icons-material/Highlight';
import LanguageIcon from '@mui/icons-material/Language';
import LinkIcon from '@mui/icons-material/Link';
import PlaylistAddCheckIcon from '@mui/icons-material/PlaylistAddCheck';
import SupervisorAccountIcon from '@mui/icons-material/SupervisorAccount';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import MapIcon from '@mui/icons-material/Map';
import * as React from 'react';
import { useState } from 'react';
import { DashboardMenuItem, MenuItemLink, useSidebarState } from 'react-admin';
import { SubMenu } from './SubMenu';
import SecurityIcon from '@mui/icons-material/Security';
import { green, red, blue, yellow } from '@mui/material/colors';
import CreateIcon from '@mui/icons-material/Create';

const Menu = ({ onMenuClick, logout, dense = false }) => {
    const [state, setState] = useState({
        menuLighthouse: false,
        menuOrgs: false,
        menuExtractor: false,
        menuSecurity: false,
    });
    const isXSmall = useMediaQuery((theme) =>
        theme.breakpoints.down('xs')
    );
    const [open] = useSidebarState();

    const handleToggle = (menu) => {
        setState(state => ({ ...state, [menu]: !state[menu] }));
    };

    return (
        <Box mt={1}>
            {' '}
            <DashboardMenuItem onClick={onMenuClick} sidebarIsOpen={open} />
            <SubMenu
                handleToggle={() => handleToggle('menuOrgs')}
                isOpen={state.menuOrgs}
                sidebarIsOpen={open}
                name="Organizations"
                icon={<SupervisorAccountIcon style={{ color: green[900] }}/>}
                dense={dense}
            >
                <MenuItemLink
                    to={`/website_user`}
                    primaryText="Websites"
                    leftIcon={<DomainIcon style={{ color: green[300] }}/>}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
            </SubMenu>
            <SubMenu
                handleToggle={() => handleToggle('menuLighthouse')}
                isOpen={state.menuLighthouse}
                sidebarIsOpen={open}
                name="Lighthouse"
                icon={<HighlightIcon style={{ color: yellow[900] }}/>}
                dense={dense}
            >
                <MenuItemLink
                    to={`/lighthouse`}
                    primaryText="Lighthouse"
                    leftIcon={<LanguageIcon style={{ color: yellow[800] }}/>}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
                <MenuItemLink
                    to={`/lighthouse_details`}
                    primaryText="Results"
                    leftIcon={<PlaylistAddCheckIcon style={{ color: yellow[700] }}/>}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
            </SubMenu>
            <SubMenu
                handleToggle={() => handleToggle('menuExtractor')}
                isOpen={state.menuExtractor}
                sidebarIsOpen={open}
                name="Extractor"
                icon={<VpnKeyIcon style={{ color: blue[900] }}/>}
                dense={dense}
            >
                <MenuItemLink
                    to={`/sitemap`}
                    primaryText="Sitemap"
                    leftIcon={<MapIcon style={{ color: blue["A700"] }}/>}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
                <MenuItemLink
                    to={`/extractor`}
                    primaryText="Images, Links, Headers"
                    leftIcon={<LinkIcon style={{ color: blue[700] }}/>}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
                <MenuItemLink
                    to={`/keywords/yake`}
                    primaryText="Yake"
                    leftIcon={<MyLocationIcon style={{ color: blue[600] }}/>}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
                
                <MenuItemLink
                    to={`/summarize`}
                    primaryText="Summarizer"
                    leftIcon={<CreateIcon style={{ color: blue[500] }}/>}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
            </SubMenu>
            
            <SubMenu
                handleToggle={() => handleToggle('menuSecurity')}
                isOpen={state.menuSecurity}
                sidebarIsOpen={open}
                name="Security"
                icon={<SecurityIcon style={{ color: red[500] }} />}
                dense={dense}
            >
                <MenuItemLink
                    to={`/security`}
                    primaryText="Security"
                    leftIcon={<SecurityIcon  style={{ color: red[300] }} />}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
                <MenuItemLink
                    to={`/security_details`}
                    primaryText="Results"
                    leftIcon={<PlaylistAddCheckIcon style={{ color: red[200] }} />}
                    onClick={onMenuClick}
                    sidebarIsOpen={open}
                    dense={dense}
                />
            </SubMenu>
            
            {isXSmall && logout}
        </Box>
    );
};

export default Menu;