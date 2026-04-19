import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BoxContainer7Component } from './box-container7.component';

describe('BoxContainer7Component', () => {
  let component: BoxContainer7Component;
  let fixture: ComponentFixture<BoxContainer7Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BoxContainer7Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BoxContainer7Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
