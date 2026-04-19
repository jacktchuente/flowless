import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BoxContainer6Component } from './box-container6.component';

describe('BoxContainer6Component', () => {
  let component: BoxContainer6Component;
  let fixture: ComponentFixture<BoxContainer6Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BoxContainer6Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BoxContainer6Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
