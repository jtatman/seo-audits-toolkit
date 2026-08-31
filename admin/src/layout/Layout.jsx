import * as React from 'react';
import { Layout, Sidebar } from 'react-admin';
import AppBar from './AppBar';
import Menu from './Menu';


const CustomSidebar = (props) => <Sidebar {...props} size={200} />;

export default (props) => (
    <Layout
        {...props}
        appBar={AppBar}
        sidebar={CustomSidebar}
        menu={Menu}
    />
);
