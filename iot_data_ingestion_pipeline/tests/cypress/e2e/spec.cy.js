import { selectors } from "@grafana/e2e";


// describe('Login test', () => {
//   it('passes', () => {
//     e2e.pages.Login.visit();
//     // To prevent flaky tests, always do a `.should` on any selector that you expect to be in the DOM.
//     // Read more here: https://docs.cypress.io/guides/core-concepts/retry-ability.html#Commands-vs-assertions
//     e2e.pages.Login.username().should('be.visible').type('admin');
//   });
// });


export const Login = {
  // Called via `Login.visit()`
  url: 'http://visib-grafa-139kq3r5417mh-850286412.eu-west-1.elb.amazonaws.com/d/lP4ilC_4k/embedded-obersvability-metrics?orgId=1&refresh=30s&from=now-15m&to=now',
  // Called via `Login.username()`
  username: 'data-testid Username input field',
};

export const Pages = {
  Login,
};

describe('Login test', () => {
  it('passes', () => {
    e2e.pages.Login.visit();
    // To prevent flaky tests, always do a `.should` on any selector that you expect to be in the DOM.
    // Read more here: https://docs.cypress.io/guides/core-concepts/retry-ability.html#Commands-vs-assertions
    pages.Login.username().should('be.visible').type('admin');
  });
});






// describe('template spec', () => {
//   beforeEach('opens login page',() => {
//     cy.visit('http://visib-grafa-1tbukqw2dz3ea-819354065.eu-west-1.elb.amazonaws.com/d/lP4ilC_4k/embedded-obersvability-metrics?orgId=1&refresh=30s&from=now-5m&to=now')
//     // cy.get("input[name=user]").type();
//     cy.get("input[name=user]").type('ADMIN');
//     cy.get("input[name=password]").type('S_!@N.eLH,(tm!HDh9")#qFlN6<aCt!f').type("{enter}");
//   })
//   it('CAN Component row', () => {
//     cy.get('[data-testid="data-testid dashboard-row-title-CAN Component Data"]').should('be.visible')
//   })
//   it('FreeRTOS Component row', () => {
//     cy.get('[data-testid="data-testid dashboard-row-title-FreeRTOS Component Data"]').should('be.visible')
//   })
//   it('FreeRTOS Component row', () => {
//     cy.get('[data-testid="data-testid dashboard-row-title-FreeRTOS Component Data"]').should('be.visible')
//   })
//   it('FreeRTOS Component row', () => {
//     cy.get('[data-testid="data-testid dashboard-row-title-FreeRTOS Component Data"]').should('be.visible')
//   })
// })