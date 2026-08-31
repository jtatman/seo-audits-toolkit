import { Box, Button, Card, CardActions, Typography } from '@mui/material';
import CodeIcon from '@mui/icons-material/Code';
import HomeIcon from '@mui/icons-material/Home';
import * as React from 'react';
import { useTranslate } from 'react-admin';
import publishArticleImage from './undraw_growth_chart.svg';

const Welcome = () => {
    const translate = useTranslate();
    return (
        <Card
            sx={{
                background: (theme) =>
                    theme.palette.mode === 'dark'
                        ? '#535353'
                        : `linear-gradient(to right, #8975fb 0%, #746be7 35%), linear-gradient(to bottom, #8975fb 0%, #6f4ceb 50%), #6f4ceb`,
                color: '#fff',
                padding: 2.5,
                marginTop: 2,
                marginBottom: '1em',
            }}
        >
            <Box display="flex">
                <Box flex="1">
                    <Typography variant="h5" component="h2" gutterBottom>
                        Welcome to OSAT ! The Open Source Audit Toolkit
                    </Typography>
                    <Box maxWidth="40em">
                        <Typography variant="body1" component="p" gutterBottom>
                            We are working hard on creating a free & Open source solution for all of your SEO issues. We'll keep on building and improving it. From SEO to NLP and Security. We'll add everything.
                        </Typography>
                    </Box>
                    <CardActions
                        sx={(theme) => ({
                            [theme.breakpoints.down('md')]: {
                                padding: 0,
                                flexWrap: 'wrap',
                                '& a': {
                                    marginTop: '1em',
                                    marginLeft: '0!important',
                                    marginRight: '1em',
                                },
                            },
                        })}
                    >
                        <Button
                            variant="contained"
                            href="https://osat.primates.dev"
                            startIcon={<HomeIcon />}
                        >
                            Documentation
                        </Button>
                        <Button
                            variant="contained"
                            href="https://github.com/StanGirard/seo-audits-toolkit"
                            startIcon={<CodeIcon />}
                        >
                            Github
                        </Button>
                    </CardActions>
                </Box>

                <Box
                    display={{ xs: 'none', sm: 'none', md: 'block' }}
                    sx={{
                        background: `url(${publishArticleImage}) top right / cover`,
                        marginLeft: 'auto',
                    }}
                    width="16em"
                    height="9em"
                    overflow="hidden"
                />
            </Box>
        </Card>
    );
};

export default Welcome;
